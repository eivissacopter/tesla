"""Vehicle identity reference data and resolver logic."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import streamlit as st

from .battery_chronology import BatteryChronologyClient


MOTOR_REFERENCE = [
    {
        'motor_code': '3D3',
        'motor_label': '3D3 / 960 Front Motor',
        'position': 'Front',
        'role': 'Front induction motor',
        'motor_type': 'Induction',
        'du_category': 'Cat 1, 2, 3',
        'stator': 'Wire (Fractional Slot)',
        'option_code': 'FD00 / FD01',
        'test_voltage_v': 335,
        'max_current_a': 630,
        'max_power_kw': 211,
        'power_30_min_kw': 65,
        'max_torque_nm': 240,
        'notes': 'Core front motor for dual-motor Model 3 and Model Y variants. Boost raises the torque cap on many Long Range cars.',
    },
    {
        'motor_code': '3D1',
        'motor_label': '3D1 / 980 Rear Performance Motor',
        'position': 'Rear',
        'role': 'Rear performance motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 1',
        'stator': 'Wire (Fractional Slot)',
        'option_code': 'RD02',
        'test_voltage_v': 320,
        'max_current_a': 840,
        'max_power_kw': 269,
        'power_30_min_kw': 90,
        'max_torque_nm': 420,
        'notes': 'Older 980 family rear performance motor. Seen on early Performance cars and some unicorn combinations.',
    },
    {
        'motor_code': '3D5',
        'motor_label': '3D5 / 990 Rear Base Motor',
        'position': 'Rear',
        'role': 'Rear base motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 1',
        'stator': 'Wire (Fractional Slot)',
        'option_code': 'RD01',
        'test_voltage_v': 335,
        'max_current_a': 715,
        'max_power_kw': 239,
        'power_30_min_kw': 88,
        'max_torque_nm': 353,
        'notes': 'Older rear base motor used on early Long Range and RWD variants.',
    },
    {
        'motor_code': '3D6',
        'motor_label': '3D6 / 740 Rear Performance Motor',
        'position': 'Rear',
        'role': 'Rear performance motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 2, 3',
        'stator': 'Hairpin',
        'option_code': 'RD06',
        'test_voltage_v': 320,
        'max_current_a': 840,
        'max_power_kw': 269,
        'power_30_min_kw': 100,
        'max_torque_nm': 450,
        'notes': 'Hairpin performance rear motor. Used in Performance trims, structural-pack Model Y, and Highland LR RWD.',
    },
    {
        'motor_code': '3D7',
        'motor_label': '3D7 / 780 Rear Base Motor',
        'position': 'Rear',
        'role': 'Rear base motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 2',
        'stator': 'Hairpin',
        'option_code': 'RD05',
        'test_voltage_v': 335,
        'max_current_a': 680,
        'max_power_kw': 227,
        'power_30_min_kw': 88,
        'max_torque_nm': 350,
        'notes': 'Hairpin base rear motor. A strong fit for modern RWD variants including Highland Model 3 RWD.',
    },
    {
        'motor_code': '4D1',
        'motor_label': '4D1 Rear Performance Motor',
        'position': 'Rear',
        'role': 'Rear performance motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 4',
        'stator': 'Hairpin',
        'option_code': None,
        'test_voltage_v': None,
        'max_current_a': 840,
        'max_power_kw': None,
        'power_30_min_kw': 125,
        'max_torque_nm': None,
        'notes': 'Cat 4 rear motor family. This family pushed German insurance and 30-minute power values noticeably higher on Model Y.',
    },
    {
        'motor_code': '4D2',
        'motor_label': '4D2 Rear Performance Motor',
        'position': 'Rear',
        'role': 'Rear performance motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 4',
        'stator': 'Hairpin',
        'option_code': None,
        'test_voltage_v': None,
        'max_current_a': None,
        'max_power_kw': None,
        'power_30_min_kw': 125,
        'max_torque_nm': None,
        'notes': 'Cat 4 rear motor used on newer Model 3 Performance approvals.',
    },
    {
        'motor_code': '4D3',
        'motor_label': '4D3 Rear Base Motor',
        'position': 'Rear',
        'role': 'Rear base motor',
        'motor_type': 'PMSRM',
        'du_category': 'Cat 4',
        'stator': 'Hairpin',
        'option_code': None,
        'test_voltage_v': None,
        'max_current_a': None,
        'max_power_kw': 220,
        'power_30_min_kw': 114,
        'max_torque_nm': 350,
        'notes': 'Cat 4 rear base motor family used on late legacy and Opal era Model Y RWD and LR AWD approvals.',
    },
]


HSN_TSN_REFERENCE = [
    {
        'hsn': '1480',
        'tsn': 'AAQ',
        'model': 'Model 3',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '3D1/3D5',
        'power_30_min_kw': '100kW',
        'insurance_power_kw': '100 kW',
        'from_year': 2019,
        'notes': 'Early Model 3 SR+ registration key.',
    },
    {
        'hsn': '1480',
        'tsn': 'AAZ',
        'model': 'Model 3',
        'version': 'SR+ / LR',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '3D5/3D7',
        'power_30_min_kw': '88kW',
        'insurance_power_kw': '88 kW',
        'from_year': 2020,
        'notes': 'Shared TSN for later Model 3 RWD trims with base rear motors.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABA',
        'model': 'Model 3',
        'version': 'Long Range',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '3D1/3D6',
        'power_30_min_kw': '90kW',
        'insurance_power_kw': '90 kW',
        'from_year': 2021,
        'notes': 'Long Range RWD approval with performance rear motor family.',
    },
    {
        'hsn': '1480',
        'tsn': 'AAR',
        'model': 'Model 3',
        'version': 'Long Range',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '3D5/3D7',
        'power_30_min_kw': '65kW+88kW',
        'insurance_power_kw': '153 kW',
        'from_year': 2019,
        'notes': 'Classic dual-motor Long Range Model 3.',
    },
    {
        'hsn': '1480',
        'tsn': 'AAS',
        'model': 'Model 3',
        'version': 'Performance',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '3D1/3D6',
        'power_30_min_kw': '65kW+90kW',
        'insurance_power_kw': '155 kW',
        'from_year': 2019,
        'notes': 'Legacy Model 3 Performance approval.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABW',
        'model': 'Model 3',
        'version': 'Performance',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '4D2',
        'power_30_min_kw': '65kW+125kW',
        'insurance_power_kw': '190 kW',
        'from_year': 2024,
        'notes': 'Newer Model 3 Performance approval with Cat 4 rear motor family.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABB',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '3D7',
        'power_30_min_kw': '88kW',
        'insurance_power_kw': '88 kW',
        'from_year': 2021,
        'notes': 'Early conventional-pack Model Y RWD.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABC',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '3D6',
        'power_30_min_kw': '100kW',
        'insurance_power_kw': '100 kW',
        'from_year': 2021,
        'notes': 'Conventional-pack Model Y RWD with stronger rear motor approval.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABS',
        'model': 'Model Y',
        'version': 'SR+ / LR',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '4D3',
        'power_30_min_kw': '114kW',
        'insurance_power_kw': '114 kW',
        'from_year': 2024,
        'notes': 'Current German key used for both Model Y RWD and LR RWD in several 2025 discussions.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABO',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '3D7',
        'power_30_min_kw': '88kW',
        'insurance_power_kw': '88 kW',
        'from_year': 2023,
        'notes': 'Structural-pack Model Y RWD with base rear motor.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABP',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '3D6',
        'power_30_min_kw': '90kW',
        'insurance_power_kw': '90 kW',
        'from_year': 2023,
        'notes': 'Structural-pack Model Y RWD with rear performance motor family.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABF',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '3D6',
        'power_30_min_kw': '100kW',
        'insurance_power_kw': '100 kW',
        'from_year': 2022,
        'notes': 'Early structural-pack Model Y RWD approval discussed around Gruenheide deliveries.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABK',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '4D1',
        'power_30_min_kw': '125kW',
        'insurance_power_kw': '125 kW',
        'from_year': 2023,
        'notes': 'Structural-pack Model Y RWD with Cat 4 rear motor.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABL',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '4D1',
        'power_30_min_kw': '127kW',
        'insurance_power_kw': '127 kW',
        'from_year': 2023,
        'notes': 'Variant of structural-pack Model Y RWD with Cat 4 rear motor.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABT',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '4D1',
        'power_30_min_kw': '125kW',
        'insurance_power_kw': '125 kW',
        'from_year': 2024,
        'notes': 'Later structural-pack Model Y RWD approval.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABX',
        'model': 'Model Y',
        'version': 'SR+',
        'drivetrain': 'RWD',
        'cat_bat': '005 / Structural',
        'front_motor': None,
        'rear_motor': '4D1',
        'power_30_min_kw': '120kW',
        'insurance_power_kw': '120 kW',
        'from_year': 2024,
        'notes': 'Later structural-pack Model Y RWD approval with lower insurance power.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABQ',
        'model': 'Model Y',
        'version': 'Long Range',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '4D1',
        'power_30_min_kw': '127kW',
        'insurance_power_kw': '127 kW',
        'from_year': 2024,
        'notes': 'Conventional-pack Model Y Long Range RWD with Cat 4 rear motor.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABU',
        'model': 'Model Y',
        'version': 'Long Range',
        'drivetrain': 'RWD',
        'cat_bat': '003 / Standard',
        'front_motor': None,
        'rear_motor': '4D3',
        'power_30_min_kw': '120kW',
        'insurance_power_kw': '120 kW',
        'from_year': 2024,
        'notes': 'Conventional-pack Model Y Long Range RWD with 4D3 rear motor family.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABD',
        'model': 'Model Y',
        'version': 'Long Range',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '3D7',
        'power_30_min_kw': '65kW+88kW',
        'insurance_power_kw': '153 kW',
        'from_year': 2021,
        'notes': 'Legacy Model Y Long Range AWD approval.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABI',
        'model': 'Model Y',
        'version': 'LR / P',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '4D1',
        'power_30_min_kw': '65kW+125kW',
        'insurance_power_kw': '190 kW',
        'from_year': 2023,
        'notes': 'Cat 4 rear motor era for Model Y Long Range AWD and some insurance lookups for Performance.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABV',
        'model': 'Model Y',
        'version': 'Long Range',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '4D3',
        'power_30_min_kw': '65kW+114kW',
        'insurance_power_kw': '179 kW',
        'from_year': 2024,
        'notes': 'New Model Y Long Range AWD key with rear 4D3 family, confirmed again in July 2024.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABE',
        'model': 'Model Y',
        'version': 'Performance',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '3D6',
        'power_30_min_kw': '65kW+90kW',
        'insurance_power_kw': '155 kW',
        'from_year': 2021,
        'notes': 'Legacy Model Y Performance approval.',
    },
    {
        'hsn': '1480',
        'tsn': 'ABJ',
        'model': 'Model Y',
        'version': 'Performance',
        'drivetrain': 'AWD',
        'cat_bat': '003 / Standard',
        'front_motor': '3D3',
        'rear_motor': '4D1',
        'power_30_min_kw': '65kW+120kW',
        'insurance_power_kw': '185 kW',
        'from_year': 2023,
        'notes': 'Cat 4 rear motor era for Model Y Performance.',
    },
]


TECH_RELEASES = [
    {
        'version_code': 'VC06',
        'effective_date': '2019-10-18',
        'release_name': 'Refresh 2020',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Refresh 2020 homologation milestone in the technical changes timeline.',
        'notes': 'Use this as an early release-family anchor when decoding older conventional approvals.',
    },
    {
        'version_code': 'VC13',
        'effective_date': '2020-10-09',
        'release_name': 'Refresh 2021',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Refresh 2021 homologation milestone in the technical changes timeline.',
        'notes': 'A strong version anchor for late-2020 and 2021 cars in Europe.',
    },
    {
        'version_code': 'VC20',
        'effective_date': '2021-11-19',
        'release_name': 'Refresh 2022',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Ryzen infotainment, 15.5V Li-Ion low-voltage battery, rear acoustic glass, new brake hardware, and updated steering controller era.',
        'notes': 'The technical changes wiki explicitly calls out Ryzen, Li-Ion low-voltage battery, rear acoustic glass, and brake updates here.',
    },
    {
        'version_code': 'VC21',
        'effective_date': '2021-12-31',
        'release_name': 'Refresh 2022 follow-up',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'MCU3 WLTP updates, Model Y gross-mass uplift by 250 kg, and a new electric power steering controller.',
        'notes': 'Useful when a user wants to know whether they are before or after the heavier Model Y approval update.',
    },
    {
        'version_code': 'VS00',
        'effective_date': '2022-06-01',
        'release_name': 'Release 2023',
        'pack_architecture': 'Structural',
        'model_scope': 'Model Y',
        'highlights': 'Switch from the old conventional approval family to the structural-pack VS-series. Rear 3D6 hairpin DU, 255 kW net, 100 kW 30-minute power, 350 V, 217 km/h.',
        'notes': 'This is the key structural-pack release marker in the technical changes wiki.',
    },
    {
        'version_code': 'VC25',
        'effective_date': '2022-08-01',
        'release_name': 'Refresh 2023',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Refresh 2023 conventional-pack homologation milestone.',
        'notes': 'Good shorthand for late-2022 conventional Model 3 and Model Y approvals.',
    },
    {
        'version_code': 'VC27',
        'effective_date': '2022-10-20',
        'release_name': 'New rear motor era',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model Y',
        'highlights': 'Introduces new base and performance rear motors, shows a Model Y Long Range with 4D5 rear motor, Model Y Performance with 4D1 rear motor, and documents the reduced-range structural Model Y period.',
        'notes': 'This is the main release marker for the switch toward Cat 4 rear motors on Model Y.',
    },
    {
        'version_code': 'VS03',
        'effective_date': '2022-10-20',
        'release_name': 'Structural rear motor update',
        'pack_architecture': 'Structural',
        'model_scope': 'Model Y',
        'highlights': 'Structural-pack companion release to VC27, still in the new rear-motor transition period.',
        'notes': 'Helpful when decoding a structural-pack 2023 Model Y from its approval code.',
    },
    {
        'version_code': 'VC32',
        'effective_date': '2023-09-04',
        'release_name': 'Refresh 2024 Highland',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3',
        'highlights': 'Highland launch marker for Model 3 in the technical changes timeline.',
        'notes': 'Use this as the cleanest version-family marker for Highland Model 3 cars.',
    },
    {
        'version_code': 'VS08',
        'effective_date': '2023-09-30',
        'release_name': 'Structural DU Cat 3 update',
        'pack_architecture': 'Structural',
        'model_scope': 'Model Y',
        'highlights': 'Adds DU Cat 3 base motors, extends the WMI with an extra digit, and introduces a new rear brake-caliper system.',
        'notes': 'This is the structural-pack release to know when a user wants to decode late-2023 structural Model Y details.',
    },
    {
        'version_code': 'VC42',
        'effective_date': '2024-10-28',
        'release_name': 'Highland 2025 battery update',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Model 3 RWD switches to CATL 6M 62.5 kWh, pushing the Chinese CLTC rating up. The same new 6M pack is already confirmed for 2025 Model Y RWD, while Model Y Long Range stays on the older LG pack.',
        'notes': 'A very useful release marker for distinguishing 6M-era RWD cars from older 6L/5L combinations.',
    },
    {
        'version_code': 'VC44',
        'effective_date': '2025-01-28',
        'release_name': 'Refresh 2025 Opal',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model Y',
        'highlights': 'Introduces the Model Y Opal Long Range AWD, a new rear-view mirror variant for legacy Model Y, and an updated drive-unit breakdown.',
        'notes': 'This is the clean version-family marker for the Opal / Juniper transition.',
    },
    {
        'version_code': 'VC45',
        'effective_date': '2025-02-26',
        'release_name': 'Opal-only lineup',
        'pack_architecture': 'Conventional',
        'model_scope': 'Model 3 / Model Y',
        'highlights': 'Removes legacy Model Y variants, adds Opal Model Y RWD and Long Range RWD approvals, confirms CATL 6M for Model Y RWD, and keeps Model Y Long Range on the older 79 kWh LG pack.',
        'notes': 'Also documents the end of the Highland Model 3 Long Range RWD base-motor variant.',
    },
]


IDENTITY_RULES = [
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2020,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '3D1/3D5',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Legacy Model 3 RWD',
        'release_code': 'VC06',
        'confidence': 'medium',
        'notes': 'Early Model 3 RWD approvals were still mixing 980 and 990-era rear motors.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2021,
        'quarter_from': 1,
        'year_to': 2023,
        'quarter_to': 3,
        'front_motor': None,
        'rear_motor': '3D6/3D7',
        'du_category': 'Cat 1/2 mix',
        'pack_architecture': 'Conventional',
        'release_family': 'Refresh 2021-2023 RWD',
        'release_code': 'VC20',
        'confidence': 'medium',
        'notes': 'This period spans the CATL 6/6L battery era and a mix of hairpin base and performance rear motors.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2023,
        'quarter_from': 4,
        'year_to': 2024,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '3D7A',
        'du_category': 'Cat 2',
        'pack_architecture': 'Conventional',
        'release_family': 'Highland',
        'release_code': 'VC32',
        'confidence': 'medium',
        'notes': 'Highland is the main release-family hint in this period, even before the 6M battery update lands.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '3D7A',
        'du_category': 'Cat 2',
        'pack_architecture': 'Conventional',
        'release_family': 'Highland 2025',
        'release_code': 'VC42',
        'confidence': 'high',
        'notes': 'The technical changes wiki explicitly ties the 2025 Model 3 RWD to CATL 6M and the 3D7A rear motor.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'year_from': 2021,
        'quarter_from': 1,
        'year_to': 2021,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '3D1/3D6',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Long Range RWD',
        'release_code': 'VC13',
        'confidence': 'medium',
        'notes': 'This is the short Model 3 Long Range RWD approval window from the HSN/TSN table.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'year_from': 2024,
        'quarter_from': 4,
        'year_to': 2025,
        'quarter_to': 1,
        'front_motor': None,
        'rear_motor': '3D6D',
        'du_category': 'Cat 2 Performance rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Highland Long Range RWD',
        'release_code': 'VC45',
        'confidence': 'high',
        'notes': 'The technical changes wiki shows the Highland LR RWD using a 3D6D performance rear motor before the variant disappears in VC45.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '3D5/3D7',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Long Range AWD',
        'release_code': 'AAR',
        'confidence': 'medium',
        'notes': 'The HSN/TSN table stays conservative here, so this rule intentionally keeps the rear-motor field broad.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'year_from': 2019,
        'quarter_from': 1,
        'year_to': 2023,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '3D1/3D6',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Legacy Performance',
        'release_code': 'AAS',
        'confidence': 'medium',
        'notes': 'Pre-2024 Model 3 Performance approvals stay in the 3D1/3D6 rear-motor family.',
    },
    {
        'market': 'Europe',
        'model': 'Model 3',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'year_from': 2024,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '4D2',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Highland Performance',
        'release_code': 'ABW',
        'confidence': 'high',
        'notes': 'Newer Model 3 Performance approvals move to a Cat 4 rear motor family.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2021,
        'quarter_from': 1,
        'year_to': 2022,
        'quarter_to': 2,
        'front_motor': None,
        'rear_motor': '3D6/3D7',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Legacy RWD',
        'release_code': 'ABB',
        'confidence': 'medium',
        'notes': 'Early conventional-pack Model Y RWD approvals are a mix of 3D6 and 3D7.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2022,
        'quarter_from': 3,
        'year_to': 2024,
        'quarter_to': 2,
        'front_motor': None,
        'rear_motor': '3D6/3D7/4D1',
        'du_category': '005 / Structural',
        'pack_architecture': 'Structural',
        'release_family': 'Structural pack',
        'release_code': 'VS00',
        'confidence': 'medium',
        'notes': 'Structural-pack Model Y RWD approvals are the most varied in this whole dataset.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2024,
        'quarter_from': 3,
        'year_to': 2024,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '4D3',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Late legacy RWD',
        'release_code': 'ABS',
        'confidence': 'medium',
        'notes': 'Conventional-pack Model Y RWD moves to 4D3 as the legacy-to-Opal bridge.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Standard',
        'drivetrain': 'RWD',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '4D3',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Opal RWD',
        'release_code': 'VC45',
        'confidence': 'high',
        'notes': 'VC45 confirms the new Model Y RWD approval and the 6M battery. German insurance threads keep pointing to TSN ABS.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'year_from': 2024,
        'quarter_from': 2,
        'year_to': 2024,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '4D1/4D3',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Long Range RWD',
        'release_code': 'ABQ/ABU',
        'confidence': 'medium',
        'notes': 'Both 4D1 and 4D3 appear in 2024 Long Range RWD approvals.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'RWD',
        'year_from': 2025,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': None,
        'rear_motor': '4D3',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Opal Long Range RWD',
        'release_code': 'VC45',
        'confidence': 'medium',
        'notes': 'The technical changes wiki confirms the approval, while German TSN threads still map many cars to ABS.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'year_from': 2021,
        'quarter_from': 1,
        'year_to': 2022,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '3D7',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Legacy Long Range AWD',
        'release_code': 'ABD',
        'confidence': 'medium',
        'notes': 'Legacy conventional Model Y LR AWD before the Cat 4 era.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'year_from': 2023,
        'quarter_from': 1,
        'year_to': 2024,
        'quarter_to': 2,
        'front_motor': '3D3',
        'rear_motor': '4D1',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Cat 4 Long Range AWD',
        'release_code': 'ABI',
        'confidence': 'high',
        'notes': 'ABI is the strong German registration clue for the pre-Opal Cat 4 Model Y LR AWD.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Long Range',
        'drivetrain': 'AWD',
        'year_from': 2024,
        'quarter_from': 3,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': '3D3A',
        'rear_motor': '4D3A',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Opal Long Range AWD',
        'release_code': 'VC44',
        'confidence': 'high',
        'notes': 'The technical changes wiki gives a very explicit Opal LR AWD motor and battery breakdown.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'year_from': 2021,
        'quarter_from': 1,
        'year_to': 2022,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '3D6',
        'du_category': '003 / Standard',
        'pack_architecture': 'Conventional',
        'release_family': 'Legacy Performance',
        'release_code': 'ABE',
        'confidence': 'medium',
        'notes': 'Legacy Model Y Performance before the Cat 4 rear-motor era.',
    },
    {
        'market': 'Europe',
        'model': 'Model Y',
        'trim': 'Performance',
        'drivetrain': 'AWD',
        'year_from': 2023,
        'quarter_from': 1,
        'year_to': 2026,
        'quarter_to': 4,
        'front_motor': '3D3',
        'rear_motor': '4D1',
        'du_category': 'Cat 4 rear',
        'pack_architecture': 'Conventional',
        'release_family': 'Cat 4 Performance',
        'release_code': 'ABJ',
        'confidence': 'high',
        'notes': 'The HSN/TSN table shows Model Y Performance moving to 4D1 from 2023 onward.',
    },
]


UNICORN_REFERENCE = [
    {
        'model': 'Model 3 Standard Range+',
        'period': 'Q4/2021',
        'variant_code': 'E6LR-P#b###',
        'why_special': 'Big CATL 6L 62 kWh LFP pack plus a 3D1A / 3D6A performance rear motor with 239 kW.',
        'notes': 'One of the best sleeper combinations for a Model 3 RWD buyer.',
    },
    {
        'model': 'Model 3 Long Range',
        'period': 'Q2/2021',
        'variant_code': 'E3LD-BGb###',
        'why_special': 'Panasonic 3L 82 kWh pack with 250 kW plateau charging, over 400 kW peak power, 640 km WLTP measured, and the nicer Q2/2021 refresh interior.',
        'notes': 'A classic battery-and-charge-curve unicorn from the technical changes wiki.',
    },
    {
        'model': 'Model 3 Performance',
        'period': 'Q1/2022',
        'variant_code': 'E3LD-PQp###',
        'why_special': 'Panasonic 3L 82 kWh pack, 3D6B Cat 2 hairpin rear motor, Ryzen MCU3, and the newer rear lights.',
        'notes': 'One of the most complete Model 3 Performance combinations in the whole timeline.',
    },
    {
        'model': 'Model Y Long Range',
        'period': 'Q3/2022 Made in Germany',
        'variant_code': 'Y5LD-BZb###',
        'why_special': 'MIG chassis tune, better front seats, 640 kg payload including the 75 kg driver assumption, and still with ultrasonic sensors.',
        'notes': 'A used-car hunter favorite because several later tradeoffs had not landed yet.',
    },
]

class VehicleIntelligenceClient:
    """Resolve Tesla vehicle identity details from curated reference data."""

    @staticmethod
    @st.cache_data
    def get_motor_df() -> pd.DataFrame:
        """Return the curated motor reference table."""
        return pd.DataFrame(MOTOR_REFERENCE)

    @staticmethod
    @st.cache_data
    def get_hsn_tsn_df() -> pd.DataFrame:
        """Return the curated HSN/TSN lookup table."""
        return pd.DataFrame(HSN_TSN_REFERENCE)

    @staticmethod
    @st.cache_data
    def get_release_df() -> pd.DataFrame:
        """Return the curated VC/VS release timeline."""
        release_df = pd.DataFrame(TECH_RELEASES)
        if not release_df.empty:
            release_df['effective_date'] = pd.to_datetime(release_df['effective_date'])
            release_df = release_df.sort_values('effective_date', ascending=False).reset_index(drop=True)
        return release_df

    @staticmethod
    @st.cache_data
    def get_unicorn_df() -> pd.DataFrame:
        """Return the curated unicorn table."""
        return pd.DataFrame(UNICORN_REFERENCE)

    @staticmethod
    @st.cache_data
    def get_identity_rule_df() -> pd.DataFrame:
        """Return the curated identity rules with sortable quarter indexes."""
        identity_df = pd.DataFrame(IDENTITY_RULES)
        if not identity_df.empty:
            identity_df['start_index'] = identity_df.apply(
                lambda row: VehicleIntelligenceClient._quarter_index(int(row['year_from']), int(row['quarter_from'])),
                axis=1,
            )
            identity_df['end_index'] = identity_df.apply(
                lambda row: VehicleIntelligenceClient._quarter_index(int(row['year_to']), int(row['quarter_to'])),
                axis=1,
            )
        return identity_df

    @staticmethod
    def list_release_codes() -> list[str]:
        """List VC/VS release codes in reverse chronological order."""
        release_df = VehicleIntelligenceClient.get_release_df()
        return release_df['version_code'].dropna().tolist()

    @staticmethod
    def list_tsn_options(model: Optional[str] = None) -> list[str]:
        """List TSN options, optionally filtered by model."""
        hsn_df = VehicleIntelligenceClient.get_hsn_tsn_df()
        if model:
            hsn_df = hsn_df[hsn_df['model'] == model]
        return sorted(hsn_df['tsn'].dropna().unique().tolist())

    @staticmethod
    def lookup_release(version_code: Optional[str]) -> pd.DataFrame:
        """Lookup a VC/VS release by code."""
        if not version_code:
            return pd.DataFrame()
        release_df = VehicleIntelligenceClient.get_release_df()
        normalized = str(version_code).strip().upper()
        return release_df[release_df['version_code'].str.upper() == normalized].copy()

    @staticmethod
    def lookup_tsn(tsn: Optional[str], model: Optional[str] = None) -> pd.DataFrame:
        """Lookup HSN/TSN information by TSN key."""
        if not tsn:
            return pd.DataFrame()
        hsn_df = VehicleIntelligenceClient.get_hsn_tsn_df()
        normalized = str(tsn).strip().upper()
        matches = hsn_df[hsn_df['tsn'].str.upper() == normalized].copy()
        if model:
            filtered = matches[matches['model'] == model].copy()
            if not filtered.empty:
                matches = filtered
        return matches

    @staticmethod
    def resolve_identity_candidates(
        market: str,
        model: str,
        trim: Optional[str],
        drivetrain: Optional[str],
        year: Optional[int],
        quarter: Optional[int],
    ) -> pd.DataFrame:
        """Resolve vehicle-identity candidates from the curated rules."""
        identity_df = VehicleIntelligenceClient.get_identity_rule_df()
        if identity_df.empty:
            return identity_df

        candidates = identity_df[
            (identity_df['market'] == market)
            & (identity_df['model'] == model)
        ].copy()
        if trim:
            candidates = candidates[candidates['trim'] == trim]
        if drivetrain:
            candidates = candidates[candidates['drivetrain'] == drivetrain]

        if year is not None and quarter is not None:
            requested_index = VehicleIntelligenceClient._quarter_index(year, quarter)
            candidates = candidates[
                (candidates['start_index'] <= requested_index)
                & (candidates['end_index'] >= requested_index)
            ].copy()
            if not candidates.empty:
                candidates['match_type'] = 'Quarter match'
        elif year is not None:
            candidates = candidates[
                (candidates['year_from'] <= year)
                & (candidates['year_to'] >= year)
            ].copy()
            if not candidates.empty:
                candidates['match_type'] = 'Year match'
        else:
            candidates['match_type'] = 'Variant match'

        if candidates.empty:
            return candidates

        candidates['sort_key'] = candidates['confidence'].map({'high': 0, 'medium': 1, 'low': 2}).fillna(9)
        return candidates.sort_values(['sort_key', 'year_from', 'quarter_from'], ascending=[True, False, False]).drop(columns=['sort_key'])

    @staticmethod
    def resolve_vehicle(
        market: str,
        model: str,
        trim: Optional[str],
        drivetrain: Optional[str],
        year: Optional[int],
        quarter: Optional[int],
        version_code: Optional[str] = None,
        tsn: Optional[str] = None,
    ) -> dict[str, Any]:
        """Resolve battery, drivetrain, release, and registration clues into one summary."""
        battery_candidates = BatteryChronologyClient.resolve_candidates(
            market=market,
            model=model,
            trim=trim,
            drivetrain=drivetrain,
            year=year,
            quarter=quarter,
        )
        identity_candidates = VehicleIntelligenceClient.resolve_identity_candidates(
            market=market,
            model=model,
            trim=trim,
            drivetrain=drivetrain,
            year=year,
            quarter=quarter,
        )
        tsn_matches = VehicleIntelligenceClient.lookup_tsn(tsn, model=model)
        release_match = VehicleIntelligenceClient.lookup_release(version_code)

        top_battery = battery_candidates.iloc[0] if not battery_candidates.empty else None
        top_identity = identity_candidates.iloc[0] if not identity_candidates.empty else None
        top_tsn = tsn_matches.iloc[0] if not tsn_matches.empty else None
        top_release = release_match.iloc[0] if not release_match.empty else None

        pack_architecture = None
        if top_tsn is not None:
            pack_architecture = 'Structural' if 'Structural' in str(top_tsn['cat_bat']) else 'Conventional'
        elif top_identity is not None:
            pack_architecture = top_identity['pack_architecture']
        elif top_release is not None:
            pack_architecture = top_release['pack_architecture']

        summary = {
            'Likely Pack': top_battery['battery_label'] if top_battery is not None else None,
            'Battery Code': top_battery['battery_code'] if top_battery is not None else None,
            'Chemistry': top_battery['chemistry'] if top_battery is not None else None,
            'Plant': top_battery['plant'] if top_battery is not None else None,
            'Front Motor': top_tsn['front_motor'] if top_tsn is not None and pd.notna(top_tsn['front_motor']) else (top_identity['front_motor'] if top_identity is not None else None),
            'Rear Motor': top_tsn['rear_motor'] if top_tsn is not None and pd.notna(top_tsn['rear_motor']) else (top_identity['rear_motor'] if top_identity is not None else None),
            'DU Category': top_identity['du_category'] if top_identity is not None else (top_tsn['cat_bat'] if top_tsn is not None else None),
            'Pack Architecture': pack_architecture,
            'Release Code': top_release['version_code'] if top_release is not None else (top_identity['release_code'] if top_identity is not None else None),
            'Release Family': top_release['release_name'] if top_release is not None else (top_identity['release_family'] if top_identity is not None else None),
            'Insurance Power': top_tsn['insurance_power_kw'] if top_tsn is not None else None,
            '30 Minute Power': top_tsn['power_30_min_kw'] if top_tsn is not None else None,
            'Confidence': top_identity['confidence'] if top_identity is not None else None,
        }

        notes: list[str] = []
        if top_identity is not None and pd.notna(top_identity['notes']):
            notes.append(str(top_identity['notes']))
        if top_release is not None and pd.notna(top_release['highlights']):
            notes.append(str(top_release['highlights']))
        if top_tsn is not None and pd.notna(top_tsn['notes']):
            notes.append(str(top_tsn['notes']))

        return {
            'summary': summary,
            'battery_candidates': battery_candidates,
            'identity_candidates': identity_candidates,
            'tsn_matches': tsn_matches,
            'release_match': release_match,
            'notes': notes,
        }

    @staticmethod
    def _quarter_index(year: int, quarter: int) -> int:
        """Convert a year and quarter into a sortable integer."""
        return year * 4 + quarter - 1
