"""Battery-care knowledge distilled from the maintained Akkuwiki + FAQ threads.

Content is translated/condensed from the German source into the app's language.
Source threads:
- Akkuwiki FAQ (WIP): https://tff-forum.de/t/wiki-akkuwiki-faq-work-in-progress/291652
- Akkuwiki Essentials:  https://tff-forum.de/t/wiki-akkuwiki-model-3-y-s-x-ct/107641
"""

FAQ_SOURCE_URL = 'https://tff-forum.de/t/wiki-akkuwiki-faq-work-in-progress/291652'

# Charging / longevity guidance per chemistry family (from the Akkuwiki "Charakteristik").
CHEMISTRY_CARE = {
    'NCA': {
        'headline': 'Daily 20–80%; 100% only when needed',
        'points': [
            'Keep everyday charging roughly 10–90%, ideally 20–80%.',
            'The 30–70% band is gentlest for calendar aging relative to usefulness.',
            "Don't leave the pack sitting at very high or very low SoC for long.",
            'Small frequent top-ups beat deep swings (e.g. 50→60% daily over 40→60% every other day).',
        ],
    },
    'NMC': {
        'headline': 'Daily 20–80%; 100% only when needed',
        'points': [
            'Keep everyday charging roughly 10–90%, ideally 20–80%.',
            'The 30–70% band is gentlest for calendar aging relative to usefulness.',
            "Don't leave the pack sitting at very high or very low SoC for long.",
            'Good cold-weather power delivery even at low SoC (LG/NMC packs).',
        ],
    },
    'LFP': {
        'headline': 'Charge to 100% regularly',
        'points': [
            'LFP can be charged to 100% without the everyday stress concerns of nickel-based packs.',
            'A regular full charge helps the BMS calibrate and read the true capacity.',
            'Variable energy buffer: usable capacity below 0% varies with charging behaviour.',
        ],
    },
}

FAQ_ENTRIES = [
    {
        'question': 'How do I calibrate my battery (BMS) correctly?',
        'answer': (
            "The range your Tesla shows says little about actual battery health — it reflects the "
            "BMS's current capacity estimate, which you can nudge over time.\n\n"
            "**Factors you can influence**\n"
            "- **Daily charge limit:** a ~60% limit calibrates the estimate upward; a 90% limit downward.\n"
            "- **Resting SoC:** always resting at the same SoC calibrates downward; varying it calibrates upward.\n"
            "- **DC fast charging:** frequent DC charging calibrates downward; rare/never calibrates upward.\n"
            "- **Cell balancing:** letting the car sleep above ~90% SoC triggers balancing; a well-balanced "
            "pack charges to a higher capacity.\n"
            "- **100% charge:** showing the BMS \"where the top is\" can calibrate upward — then return to "
            "≤90% (better 60%) promptly.\n"
            "- **Full discharge then slow full charge:** can help the BMS relearn true capacity.\n\n"
            "**Factors you can't fully control:** ambient temperature (reports conflict) and software updates "
            "(which can reset or change learned values)."
        ),
    },
    {
        'question': 'Why do Tesla owners share their km reading at 100% SoC?',
        'answer': (
            "Displayed range (\"Rated Range\") isn't based on your driving — it's a fixed per-model constant. "
            "**Rated Range × Rated Consumption = the BMS's current pack capacity.**\n\n"
            "*Example:* 500 km shown × 200 Wh/km constant = 100 kWh current capacity.\n\n"
            "Only valid when charged to a true 100% (\"charging complete\") and read then — not by dragging "
            "the charge-limit slider in the app."
        ),
    },
    {
        'question': "Why doesn't my car show the advertised (WLTP) range at 100%?",
        'answer': (
            "The European (D-A-CH) Tesla site advertises **WLTP** range; the US site uses **EPA**. The car "
            "computes Rated Range from its current capacity ÷ the **US EPA** consumption constant, so the "
            "number matches EPA rather than WLTP.\n\n"
            "It can be lower still when the equivalent EU car has a smaller pack — e.g. Model 3 Refresh "
            "US (77.8 kWh / 567 km) vs EU (75.9 kWh / 554 km), same 137 Wh/km constant."
        ),
    },
    {
        'question': 'How is the hidden Energy Buffer calculated?',
        'answer': (
            "The **energy buffer** is usable capacity hidden below 0% SoC — typically **~4.5%** of net "
            "capacity (≈4.5 kWh on a 100 kWh pack). It's an emergency reserve you should never plan to use.\n\n"
            "Tesla folds it into displayed range proportionally to SoC: at 100% the full buffer is added to "
            "range, at 50% half, at 0% none — so the car shows 0 km with the buffer still physically available."
        ),
    },
]

# Degradation science — consensus from peer-reviewed Li-ion aging research, mapped to
# the fields this app tracks. Educational summary, not personalized advice.
SCIENCE_TOPICS = [
    {
        'icon': '🌡️',
        'title': 'Temperature',
        'summary': 'Temperature is the strongest environmental driver of aging — both extremes hurt, for different reasons.',
        'findings': [
            'Heat accelerates parasitic side reactions: SEI growth and electrolyte oxidation follow roughly an '
            'Arrhenius law, so calendar fade rises steeply with temperature (often on the order of ~2× per +10 °C).',
            'Cold is dangerous *while charging*: slow lithium diffusion promotes metallic **lithium plating** on '
            'the anode, which is partly irreversible and a safety risk. Post-mortem work finds an aging minimum '
            'near ~25 °C — plating-dominated below it, SEI/cathode-dominated above.',
            'Practical sweet spot is roughly 15–35 °C; cells prefer slightly above room temperature. Avoid hard '
            'charging when very cold and prolonged heat-soak at high SoC.',
        ],
        'app_tie': 'Long-term thermal exposure is baked into the Degradation-vs-Age and per-cycle trends you see here.',
        'evidence': 'Waldmann et al. 2014; Vetter et al. 2005.',
    },
    {
        'icon': '🔋',
        'title': 'State of charge & cell voltage',
        'summary': 'Time spent at high SoC (high cell voltage) is the dominant calendar-aging stressor.',
        'findings': [
            'Higher SoC means higher cathode potential, which speeds electrolyte oxidation, SEI growth and '
            'transition-metal dissolution. Calendar fade climbs sharply above ~70–80% SoC, and far worse combined with heat.',
            'Sitting near 100% is the most damaging everyday habit for nickel-rich (NCA/NMC) cells; the ~30–70% '
            'band minimizes calendar aging.',
            "LFP's lower, flatter voltage makes it much more tolerant of high SoC — which is why charging it to "
            '100% is fine and even useful for BMS calibration.',
        ],
        'app_tie': 'Maps directly to the **Daily SOC Limit** filter — higher limits are expected to track with faster degradation.',
        'evidence': 'Keil et al. 2016; Schmalstieg et al. 2014.',
    },
    {
        'icon': '⚡',
        'title': 'Charge rate (C-rate) & fast charging',
        'summary': 'High currents add heat and overpotential; high charge rates promote lithium plating.',
        'findings': [
            'Higher C-rate raises internal heating (I²R) and electrode overpotentials, accelerating SEI growth '
            'and mechanical stress.',
            'High **charge** C-rate is especially harmful when cold — the classic trigger for lithium plating. A '
            'high lifetime fraction of DC fast charging measurably increases capacity fade versus AC charging.',
            'Modern Tesla packs precondition and thermally manage for Supercharging, so occasional DC charging is '
            'fine — but the cumulative fast-charge fraction still adds up.',
        ],
        'app_tie': 'Maps to the **DC Ratio** filter — a higher fast-charge fraction is expected to correlate with more degradation.',
        'evidence': 'Vetter et al. 2005; Waldmann et al. 2014.',
    },
    {
        'icon': '🔄',
        'title': 'Depth of discharge & cycles',
        'summary': 'Shallow cycles age a cell far less than deep ones per unit of energy delivered.',
        'findings': [
            'Mechanical stress from lattice expansion/contraction scales with depth of discharge; deep 0–100% '
            'cycling cracks particles and loses contact more than shallow mid-SoC cycles.',
            'Cycle life is best expressed in **equivalent full cycles** — many shallow cycles deliver more total '
            'distance than a few deep ones before reaching the same fade.',
            'Practical upshot: small, frequent top-ups in the mid band beat deep swings.',
        ],
        'app_tie': 'Relates to the **Cycles** axis and the degradation-per-cycle view.',
        'evidence': 'Vetter et al. 2005.',
    },
    {
        'icon': '🔬',
        'title': 'What is actually degrading',
        'summary': 'Capacity fade is mostly lost cyclable lithium; power fade is mostly rising resistance.',
        'findings': [
            '**SEI growth** on the anode consumes lithium inventory — the main cause of gradual calendar capacity loss.',
            '**Lithium plating** (cold or fast charging) removes cyclable lithium and can seed dendrites.',
            '**Cathode degradation** — particle cracking, transition-metal dissolution, structural change — worsens '
            'at high voltage and temperature.',
            'Rising internal impedance and loss of active material reduce usable energy and peak power over time.',
        ],
        'app_tie': 'Why SOH (capacity) and power capability fade on different timescales.',
        'evidence': 'Vetter et al. 2005; Schmalstieg et al. 2014.',
    },
]

# Representative, foundational peer-reviewed works (no fabricated DOIs).
LITERATURE = [
    'Vetter et al. (2005), *Journal of Power Sources* — “Ageing mechanisms in lithium-ion batteries” (foundational review).',
    'Waldmann et al. (2014), *Journal of Power Sources* — temperature-dependent aging / post-mortem study (the ~25 °C minimum, plating below it).',
    'Keil et al. (2016), *Journal of The Electrochemical Society* — calendar aging vs. state of charge.',
    'Schmalstieg et al. (2014), *Journal of Power Sources* — holistic NMC 18650 aging model (SoC, voltage and temperature stress factors).',
    'Harlow, Dahn et al. (2019), *Journal of The Electrochemical Society* — long-term benchmark cell testing (Dahn group).',
]
