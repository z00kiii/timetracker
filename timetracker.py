from datetime import datetime, timedelta
import os
from notion_client import Client
from dotenv import load_dotenv
import argparse
import plotly.graph_objects as go


########################## Setup ########################################

# example goals for activities
DAILY_GOAL_FOR_CAT = {
    "write": "00:30",
    "workout": "01:00",
    "daily": "00:30",
    "meditate": "00:30",
    "social": "01:00",
    "life": "01:45",
    "read": "00:30",
    "me": "2:00",
    "sleep": "08:00",
    "work": "07:00",
}

# import private goals
from goals import DAILY_GOAL_FOR_CAT

# load content from .env file
load_dotenv()

TIMETRACKER_DB_ID = os.getenv("TIMETRACKER_DB_ID")

# create argparser
parser = argparse.ArgumentParser()
parser.add_argument(
    "--timeframe",
    choices=["this", "past"],
    default="past",
    help="timeframe: 'this' or 'past'",
)
parser.add_argument(
    "--period",
    choices=["day", "week", "month"],
    default="week",
    help="period: 'day', 'week' or 'month",
)

# parse args
args = parser.parse_args()

# setup notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

########################## DB Access ########################################

# set filter and sorts according to params
if args.period == "day":
    date = (
        datetime.now()
        if args.timeframe == "this"
        else datetime.now() - timedelta(days=1)
    )
    date = date.strftime("%Y-%m-%d")

    filter_params_scope = {"equals": date}
else:
    filter_params_scope = {f"{args.timeframe}_{args.period}": {}}

filter_params = {
    "property": "Date",
    "date": filter_params_scope,
}

sorts = [{"property": "Date", "direction": "descending"}]

# database query with pagination
entries = []
start_cursor = None

while True:
    timetracks = notion.databases.query(
        database_id=TIMETRACKER_DB_ID,
        filter=filter_params,
        sorts=sorts,
        start_cursor=start_cursor,
    )
    entries.extend(timetracks["results"])

    if not timetracks["has_more"]:
        break

    start_cursor = timetracks["next_cursor"]

# ['object', 'results', 'next_cursor', 'has_more', 'type', 'page_or_database', 'request_id']

# get database properties for creation of time_for_cat dict
db = notion.databases.retrieve(database_id=TIMETRACKER_DB_ID)

########################## Data interpretation ########################################

# set properties in same order as in notion
time_for_cat = {}
for prop in db["properties"]["Category"]["select"]["options"]:
    time_for_cat[prop["name"]] = 0

events = []

days = set()

# calc durations of activities
for idx, entry in enumerate(entries):
    # set end_time
    if idx == 0:
        end_time = datetime.now()  # TODO make it the last day for 'past' requests
    else:
        end_time = start_time - timedelta(
            minutes=1
        )  # start_time - 1 of previous entry is end_time of current entry

    # get cat and start_time of current entry
    cat = entry["properties"]["Category"]["select"]["name"]
    start_time_str = entry["properties"]["Date"]["date"]["start"]
    start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=None)

    duration = end_time - start_time
    time_for_cat[cat] += duration.seconds

    # List with cat, name, start, end, duration
    events.append(
        {
            "name": entry["properties"]["Name"]["title"][0]["plain_text"],
            "cat": cat,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "color": entry["properties"]["Category"]["select"]["color"],
        }
    )

    # set of uniqe days
    days.add(start_time.date())

########################## Formatting and printing ########################################

# format to HH:mm
time_for_cat_formatted = {}
for cat in time_for_cat:
    time_for_cat_formatted[cat] = "{:02}:{:02}".format(
        time_for_cat[cat] // 3600, (time_for_cat[cat] % 3600) // 60
    )

# get number of analized days
days_period = len(days)
# calc the current day as relative
if days_period > 1:
    days_period = days_period - 1 + (datetime.now().time().hour) / 24


# print results
print(f"Results for the last {days_period} day(s)")
print(
    "{:<12} {:<12} {:<12} {:<12}".format("category", "total time", "time / day", "goal")
)
print("---------------------------------------------")
for cat in time_for_cat:
    print(
        "{:<12} {:<12} {:<12} {:<12}".format(
            cat,
            time_for_cat_formatted[cat],
            "{:02}:{:02}".format(
                int(time_for_cat[cat] // (3600 * days_period)),
                int(
                    int((time_for_cat[cat] % (3600 * days_period)))
                    // (60 * days_period)
                ),
            ),
            DAILY_GOAL_FOR_CAT[cat] if cat in DAILY_GOAL_FOR_CAT else "--:--",
        )
    )
