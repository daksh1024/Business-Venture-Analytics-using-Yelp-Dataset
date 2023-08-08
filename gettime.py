#getting popular timings

import json
import ast
import numpy as np
from statistics import mean
import pandas as pd

avg_start = []
avg_end = []

def popular_time(df):
    global avg_start
    global avg_end
    #this works so don't change it
    df['hours'] = df['hours'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)

    mon_start = []
    mon_end = []
    tue_start = []
    tue_end = []
    wed_start = []
    wed_end = []
    thur_start = []
    thur_end = []
    fri_start = []
    fri_end = []
    sat_start = []
    sat_end = []
    sun_start = []
    sun_end = []
    start = "-"
    end = ":"

    for time in df['hours']:

        if not pd.isnull(time):
            if "Monday" in time:
                mon_start.append(time['Monday'].split(":")[0])
                mon_end.append(time['Monday'][time['Monday'].find(start)+len(start):time['Monday'].rfind(end)])
            if "Tuesday" in time:
                tue_start.append(time['Tuesday'].split(":")[0])
                tue_end.append(time['Tuesday'][time['Tuesday'].find(start)+len(start):time['Tuesday'].rfind(end)])
            if "Wednesday" in time:
                wed_start.append(time['Wednesday'].split(":")[0])
                wed_end.append(time['Wednesday'][time['Wednesday'].find(start)+len(start):time['Wednesday'].rfind(end)])
            if "Thursday" in time:
                thur_start.append(time['Thursday'].split(":")[0])
                thur_end.append(time['Thursday'][time['Thursday'].find(start)+len(start):time['Thursday'].rfind(end)])
            if "Friday" in time:
                fri_start.append(time['Friday'].split(":")[0])
                fri_end.append(time['Friday'][time['Friday'].find(start)+len(start):time['Friday'].rfind(end)])
            if "Saturday" in time:
                sat_start.append(time['Saturday'].split(":")[0])
                sat_end.append(time['Saturday'][time['Saturday'].find(start)+len(start):time['Saturday'].rfind(end)])
            if "Sunday" in time:
                sun_start.append(time['Sunday'].split(":")[0])
                sun_end.append(time['Sunday'][time['Sunday'].find(start)+len(start):time['Sunday'].rfind(end)])

    start_list = [mon_start, tue_start, wed_start, thur_start, fri_start, sat_start, sun_start]
    for item in start_list:
        add_to_start_list(item)

    end_list = [mon_end, tue_end, wed_end, thur_end, fri_end, sat_end, sun_end]
    for item in end_list:
        add_to_end_list(item)

    return avg_start, avg_end

def add_to_start_list(start_list):
    global avg_start
    start_list = list(map(int, start_list))
    res = remove_items(start_list, 0)
    avg_start.append(round(mean(res)))

def add_to_end_list(end_list):
    global avg_end
    end_list = list(map(int, end_list))
    res = remove_items(end_list, 0)
    avg_end.append(round(mean(res)))

def remove_items(input_list, item):

    # remove the item for all its occurrences
    c = input_list.count(item)
    for i in range(c):
        input_list.remove(item)

    return input_list