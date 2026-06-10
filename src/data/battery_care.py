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
