import sys, datetime
sys.path.insert(0, '.')
from etl.identity import resolve_identity

# Real cars (vin, trim_badge, car_type, approx first_seen month)
cars = [
 ("Morty#6","XP7YGCEKXRB268805","74d","modely", datetime.datetime(2024,5,1)),
 ("X_Molli","XP7YGCEJ9PB137966","50","modely", datetime.datetime(2023,2,1)),
 ("X_Morty#1","LRWYGCEK4MC065820","74d","modely", datetime.datetime(2021,6,1)),
 ("X_Rick#5","LRW3E7EL3NC489250","p74d","model3", datetime.datetime(2022,7,1)),
 ("X_Rick#1","5YJ3E7ECXLF683812","p74d","model3", datetime.datetime(2020,9,1)),
]
for name, vin, badge, ctype, fs in cars:
    pid = resolve_identity(vin, badge, ctype, fs)
    print(f"\n{name}: {pid.label()}")
    print(f"   pack={pid.pack_label} | code={pid.battery_code} | chem={pid.chemistry} "
          f"| motors={pid.front_motor}/{pid.rear_motor} | release={pid.release_family} | conf={pid.confidence}")
