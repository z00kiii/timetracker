from datetime import datetime, timedelta
import os
from notion_client import Client
from dotenv import load_dotenv
import argparse
import plotly.graph_objects as go


########################## Setup ########################################

# notion colors to rgb
COLOR_NAME_TO_RGB = {
    "default": "rgb(55, 55, 55)",
    "gray": "rgb(90, 90, 90)",
    "brown": "rgb(91, 61, 47)",
    "orange": "rgb(125, 79, 39)",
    "yellow": "rgb(140, 110, 52)",
    "green": "rgb(55, 95, 65)",
    "blue": "rgb(47, 68, 105)",
    "purple": "rgb(69, 48, 97)",
    "pink": "rgb(98, 52, 75)",
    "red": "rgb(103, 57, 50)",
}

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

# load content from .env file
load_dotenv()

# setup notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))
TIMETRACKER_DB_ID = os.getenv("TIMETRACKER_DB_ID")

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

########################## Plotting ########################################

# reverse for easier use
events = reversed(events)


def calculate_durations(event):
    start_time = event["start_time"]
    duration_hours = event["duration"].total_seconds() / 3600
    end_time = event["end_time"]
    name = event["name"]
    color = COLOR_NAME_TO_RGB[event["color"]]

    if start_time.day != end_time.day:
        end_of_first_day = datetime(
            start_time.year, start_time.month, start_time.day, 23, 59, 59
        )
        first_day_duration_hours = (
            end_of_first_day - start_time
        ).total_seconds() / 3600

        next_day_duration_hours = duration_hours - first_day_duration_hours

        return [
            (start_time.date(), first_day_duration_hours, name, color),
            (
                (start_time + timedelta(days=1)).date(),
                next_day_duration_hours,
                name,
                color,
            ),
        ]
    else:
        return [(start_time.date(), duration_hours, name, color)]


data = [item for event in events for item in calculate_durations(event)]

x, y, labels, colors = zip(*data)

fig = go.Figure(
    data=[go.Bar(x=x, y=y, text=labels, marker_color=colors, textposition="auto")]
)
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Time",
    xaxis=dict(side="top", tickfont=dict(color="white")),
    yaxis=dict(
        autorange="reversed",
        tickfont=dict(color="white"),
        tickmode="array",
        tickvals=list(range(24)),  # Hours from 0 to 23
        ticktext=[f"{i}'" for i in range(24)],
    ),
    shapes=[
        dict(
            type='line',
            xref='paper',
            yref='y',
            x0=0,
            y0=i + 0.5,  # Position at every half hour
            x1=1,
            y1=i + 0.5,
            line=dict(
                color='rgb(40,40,40)',
                width=1,
            ),
            layer='below', 
        ) for i in range(23)  # For each hour, add a half-hour mark
    ],
    plot_bgcolor="rgb(17,17,17)",
    paper_bgcolor="rgb(17,17,17)",
    font=dict(color="white"),
    margin=dict(l=50, r=50, t=50, b=50),
    hoverlabel=dict(
        bgcolor="black", font=dict(color="white")
    ),
    legend=dict(font=dict(color="white")),
    title=dict(font=dict(color="white")),
    yaxis_showgrid=True,
    xaxis_showgrid=True,
    xaxis_gridcolor="rgb(50,50,50)",
    yaxis_gridcolor="rgb(50,50,50)",
    yaxis_zeroline=True,
    xaxis_zeroline=True,
    yaxis_zerolinecolor="rgb(50,50,50)",
    xaxis_zerolinecolor="rgb(50,50,50)",
)
fig.update_traces(marker_line_color="rgb(50,50,50)", marker_line_width=0.5)

fig.show()

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
if args.period == "day":
    date = datetime.fromisoformat(entries[-1]["properties"]["Date"]["date"]["start"])
    print(f"started day at {date.hour}:{date.minute}")
else:
    print(f"results for the last {days_period} days")
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
