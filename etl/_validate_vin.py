import sys
sys.path.insert(0, '.')
from etl.vin import decode_vin

# (display_name, vin, trim_badge) straight from the live cars table
rows = [
 ("Morty#6","XP7YGCEKXRB268805","74d"),
 ("X_Molli","XP7YGCEJ9PB137966","50"),
 ("X_Morty#1","LRWYGCEK4MC065820","74d"),
 ("X_Morty#4","XP7YGCEK1NB017391","74d"),
 ("X_Rick#1","5YJ3E7ECXLF683812","M3 LR P"),
 ("X_Rick#5","LRW3E7EL3NC489250","p74d"),
 ("X_Molli","XP7YGCEJ9PB137966","50"),
]
print(f"{'car':12} {'model':9} {'yr':4} {'factory':8} {'drv':4} {'trim':6} valid")
print("-"*55)
for name, vin, trim in rows:
    d = decode_vin(vin)
    print(f"{name:12} {str(d.model):9} {str(d.model_year):4} {str(d.factory_code):8} {str(d.drivetrain_hint):4} {trim:6} {d.valid}")
