#!/usr/bin/env python3


import argparse
import json

import matplotlib.pyplot as plot
import pandas
import seaborn


parser = argparse.ArgumentParser()
parser.add_argument(
    "export_data",
    help="path to the exported chat messages (a json file)",
    type=str)
args = parser.parse_args()


# Read the export results and read the message into a data frame.
with open(args.export_data) as fd:
    chat = json.load(fd)


df = pandas.DataFrame(
    message
    for message in chat["messages"]
    if message["type"] == "message")
df["date"] = pandas.to_datetime(df["date"])


# This is an empty context we are going to populate with template
# data.
context = {}


# 0. Chat title and dates.
context["title"] = chat["name"]
context["date_from"] = df["date"].min()
context["date_to"] = df["date"].max()


# 1. Top 10 posters.
context["top_posters"] = (
    df.groupby(["from", "from_id"])
      .size()
      .sort_values(ascending=False)
      .head(10))


# 2. Messages per hour, full timeline
day = df["date"].dt.floor("D")
context["timeline"] = day.groupby(day).size()


# 3. Messages per hour, daily mean
hour = df["date"].dt.floor("H")
rate = hour.groupby(hour).size()
context["daily"] = rate.groupby(lambda ts: ts.hour).mean()


plot.figure(1)
seaborn.lineplot(
    x=context["timeline"].index,
    y=context["timeline"].values)

plot.figure(2)
seaborn.lineplot(
    x=context["daily"].index,
    y=context["daily"].values)

plot.show()
