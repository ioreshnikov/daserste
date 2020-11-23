#!/usr/bin/env python3


import argparse
import json
import os
import re

import emoji
import matplotlib.pyplot as plot
import pandas
import seaborn
import telegram

import settings


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


# A bit of preprocessing. Let us extract the swearwords. We load the
# obscenity corpus from the external file.
with open(settings.obscene_corpus) as fd:
    obscene_corpus = set(line.strip().lower() for line in fd)

# And then we go through every message and do the following:
# 1. We split the message into individual words.
# 2. We look for profanity in there.
# 3. We also extract individual emojis.
# All this data we dump into individual lists and then we add it to
# the dataframe as columns.

emojis_column = []
swearwords_column = []
words_column = []

for index, row in enumerate(df.itertuples()):
    if isinstance(row.text, str):
        text = row.text
    elif isinstance(row.text, list):
        for entry in row.text:
            if isinstance(entry, str):
                text = entry
                break
        else:
            emojis_column.append([])
            swearwords_column.append([])
            words_column.append([])
            continue

    words = re.findall(r"\w+", text.lower())
    swearwords = [
        word for word in words if word in obscene_corpus
    ]
    words_column.append(words)
    swearwords_column.append(swearwords)

    emojis = [char for char in text if char in emoji.UNICODE_EMOJI]
    emojis_column.append(emojis)

df["emojis"] = pandas.Series(emojis_column)
df["words"] = pandas.Series(words_column)
df["swearwords"] = pandas.Series(swearwords_column)
df["n_words"] = pandas.Series(len(words) for words in words_column)
df["n_swearwords"] = pandas.Series(
    len(swearwords) for swearwords in swearwords_column)


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


# 4. Now, the fun part. Top stickers
context["top_stickers"] = (
    df[df["media_type"] == "sticker"]
      .groupby("file")
      .size()
      .sort_values(ascending=False)
      .head(10))


# 5. Top emojis.
emojis = pandas.Series(df["emojis"].sum())
context["top_emojis"] = (
    emojis
      .groupby(emojis)
      .size()
      .sort_values(ascending=False)
      .head(10))


# 6. Top swearwords.
swearwords = pandas.Series(df["swearwords"].sum())
context["top_swearwords"] = (
    swearwords
      .groupby(swearwords)
      .size()
      .sort_values(ascending=False)
      .head(10))


# 7. Top swearers
swearwords_total = (
    df[["from", "from_id", "n_words", "n_swearwords"]]
      .groupby(["from", "from_id"])
      .sum())
swearwords_total = swearwords_total[swearwords_total["n_words"] > 100]
context["top_swearers"] = (
    (swearwords_total["n_swearwords"] / swearwords_total["n_words"])
      .sort_values(ascending=False)
      .head(10))


os.makedirs("report", exist_ok=True)
