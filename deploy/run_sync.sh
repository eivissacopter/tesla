#!/usr/bin/env bash
# Weekly sync entrypoint: export the anonymized artifact, then publish it.
#
# Modes:
#   RUN_MODE=once  -> run a single export+publish and exit (use with an external
#                     scheduler / Unraid User Scripts / host cron).
#   RUN_MODE=loop  -> run now, then sleep SYNC_INTERVAL_SECONDS and repeat
#                     (self-contained weekly loop; default).
set -euo pipefail

OUT_DIR="${OUT_DIR:-/data/teslatech}"
PUBLISH_TARGETS="${PUBLISH_TARGETS:-postgres}"   # e.g. "postgres s3" (space separated)
RUN_MODE="${RUN_MODE:-loop}"
SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-604800}"   # 7 days

run_once() {
  echo "[sync] $(date -u +%FT%TZ) exporting fleet artifact..."
  python -m etl.export_fleet --out "$OUT_DIR"
  echo "[sync] exporting telemetry cloud..."
  python -m etl.export_telemetry --out "$OUT_DIR" --days "${TELEMETRY_DAYS:-365}" \
    --bin-seconds "${TELEMETRY_BIN_SECONDS:-20}" --max-points "${TELEMETRY_MAX_POINTS:-3000}" || \
    echo "[sync] telemetry export had issues (continuing)"
  for t in $PUBLISH_TARGETS; do
    echo "[sync] publishing fleet -> $t"
    python -m etl.publish --artifact "$OUT_DIR/fleet.json" --table fleet_artifacts --target "$t"
    if [ -f "$OUT_DIR/telemetry.json" ]; then
      echo "[sync] publishing telemetry -> $t"
      python -m etl.publish --artifact "$OUT_DIR/telemetry.json" --table fleet_telemetry --target "$t"
    fi
  done
  echo "[sync] done."
}

if [ "$RUN_MODE" = "once" ]; then
  run_once
else
  while true; do
    run_once || echo "[sync] run failed; will retry next interval"
    echo "[sync] sleeping ${SYNC_INTERVAL_SECONDS}s until next sync"
    sleep "$SYNC_INTERVAL_SECONDS"
  done
fi
