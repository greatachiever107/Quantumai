"""Build events/events.csv - a calendar of scheduled US market-moving events.

Run from the project folder:
    python build_events.py

Included automatically:
  FOMC - Fed interest-rate decision days (2016-2026). The 2021-2026 dates were
         checked against federalreserve.gov; 2016-2020 are from the Fed's
         historical calendars (the script sanity-checks weekdays).
  NFP  - US jobs report (Non-Farm Payrolls), computed from the BLS rule
         "third Friday after the week containing the 12th", with the usual
         holiday fixes. Months disrupted by the Oct-Nov 2025 US government
         shutdown are left out. Spot-check against bls.gov if it matters.

Add anything else (CPI, GDP, earnings, wars, elections...) in a file called
events/extra_events.csv with columns:  date,event
e.g.   2026-10-14,CPI
Anything in that file is merged in, and every distinct event name is analysed
separately by event_study.py.
"""
import os
import datetime as dt
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

FOMC = """
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-03-03 2020-03-15 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09
""".split()

# decision days that are legitimately not a Wednesday (election weeks, emergencies)
KNOWN_NON_WED = {"2018-11-08", "2020-03-03", "2020-03-15", "2020-11-05", "2024-11-07"}
NFP_SKIP = {"2025-10-03", "2025-11-07"}      # shutdown-disrupted releases

rows = []
for d in FOMC:
    day = pd.Timestamp(d)
    if day.weekday() != 2 and d not in KNOWN_NON_WED:
        print(f"WARNING: FOMC date {d} is a {day.day_name()} - please check it")
    rows.append((day, "FOMC"))

holidays = set(USFederalHolidayCalendar().holidays("2015-01-01", "2027-12-31"))
for year in range(2015, 2027):
    for month in range(1, 13):
        ref = dt.date(year, month, 12)
        sat = ref + dt.timedelta(days=(5 - ref.weekday()) % 7)   # Saturday ending the reference week
        rel = pd.Timestamp(sat + dt.timedelta(days=20))          # third Friday after
        if rel.month == 1 and rel.day <= 3:                      # New Year fix
            rel += pd.Timedelta(days=7)
        if rel in holidays:                                      # holiday -> day before
            rel -= pd.Timedelta(days=1)
        if rel.year < 2016 or rel.year > 2026 or str(rel.date()) in NFP_SKIP:
            continue
        rows.append((rel, "NFP"))

ev = pd.DataFrame(rows, columns=["date", "event"])

extra = "events/extra_events.csv"
if os.path.exists(extra):
    x = pd.read_csv(extra, parse_dates=["date"])
    ev = pd.concat([ev, x[["date", "event"]]])
    print(f"Merged {len(x)} extra events from {extra}")

ev = ev.drop_duplicates().sort_values("date").reset_index(drop=True)
os.makedirs("events", exist_ok=True)
ev.to_csv("events/events.csv", index=False)
print(ev["event"].value_counts().to_string())
print(f"\nSaved events/events.csv ({len(ev)} events)")
