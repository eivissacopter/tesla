"""Pluggable read-only access to the Teslalogger MariaDB.

Two backends, one interface (``read_sql(query) -> DataFrame``):

* ``SqlAlchemyReader`` -- a direct connection, used in production when the ETL
  runs *on the home server* on the Docker network (host ``teslalogger-db``).
* ``SshMysqlReader`` -- runs ``docker exec teslalogger-db mysql`` over an SSH
  (plink) connection, used for development from a workstation that cannot reach
  the Docker-internal database port. Heavy aggregation is pushed into SQL so
  only small result sets cross the wire.

Both are strictly read-only.
"""

from __future__ import annotations

import io
import subprocess
import time
from typing import Optional

import pandas as pd


class DbReader:
    def read_sql(self, query: str) -> pd.DataFrame:  # pragma: no cover - interface
        raise NotImplementedError


class SqlAlchemyReader(DbReader):
    """Direct connection. Used on the home server / inside a container."""

    def __init__(self, user: str, password: str, host: str, port: int | str,
                 db: str, driver: str = "mysql+pymysql"):
        from sqlalchemy import create_engine
        self._engine = create_engine(
            f"{driver}://{user}:{password}@{host}:{port}/{db}",
            pool_pre_ping=True,
        )

    def read_sql(self, query: str) -> pd.DataFrame:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            try:
                conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
            except Exception:
                pass
            return pd.read_sql_query(text(query), conn)


class SshMysqlReader(DbReader):
    """Run mysql inside the DB container over SSH (plink) and parse TSV.

    Development backend. Aggregate in SQL; do not pull raw multi-million-row
    tables through this path.
    """

    def __init__(self, plink: str, host: str, port: int, user: str, password: str,
                 container: str = "teslalogger-db",
                 db_user: str = "teslalogger", db_pass: str = "teslalogger",
                 db_name: str = "teslalogger"):
        self.plink = plink
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.container = container
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name

    def read_sql(self, query: str) -> pd.DataFrame:
        one_line = " ".join(query.split())
        # mysql -e "<sql>" emits TSV with a header row.
        remote = (
            f'docker exec {self.container} mysql -u{self.db_user} '
            f'-p{self.db_pass} {self.db_name} --batch --raw -e "{one_line}"'
        )
        cmd = [
            self.plink, "-ssh", "-batch", "-P", str(self.port),
            "-pw", self.password, f"{self.user}@{self.host}", remote,
        ]
        last_err = ""
        for attempt in range(3):
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0:
                out = proc.stdout
                if not out.strip():
                    return pd.DataFrame()
                return pd.read_csv(io.StringIO(out), sep="\t", na_values=["NULL"])
            last_err = proc.stderr.strip()[:400]
            time.sleep(2 * (attempt + 1))   # transient reset backoff
        raise RuntimeError(f"SSH query failed after retries: {last_err}")


def make_reader_from_env() -> DbReader:
    """Build a reader from environment.

    TESLATECH_DB_MODE = 'direct' -> SqlAlchemyReader (uses DB_* vars)
                        'ssh'    -> SshMysqlReader   (uses SSH_* vars)
    """
    import os
    mode = os.environ.get("TESLATECH_DB_MODE", "ssh").lower()
    if mode == "direct":
        return SqlAlchemyReader(
            user=os.environ.get("DB_USER", "teslalogger"),
            password=os.environ.get("DB_PASS", "teslalogger"),
            host=os.environ.get("DB_HOST", "teslalogger-db"),
            port=os.environ.get("DB_PORT", "3306"),
            db=os.environ.get("DB_NAME", "teslalogger"),
        )
    return SshMysqlReader(
        plink=os.environ.get("PLINK", r"C:\Program Files\PuTTY\plink.exe"),
        host=os.environ.get("SSH_HOST", "192.168.178.99"),
        port=int(os.environ.get("SSH_PORT", "69")),
        user=os.environ.get("SSH_USER", "root"),
        password=os.environ["SSH_PASS"],
    )
