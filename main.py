#imports
from flask import Flask, render_template, request, url_for, flash, redirect, Response
import json
from google.cloud import bigquery
import os
import pandas as pd
import requests
from statistics import mean
from wtforms import StringField, Form
from credentials import sql_engine, geo_code, sec_key, bigquery_cred
from math import radians, sin, cos, sqrt, atan2
from memory_profiler import profile
import time
import multiprocess as mp
import multiprocessing
from threading import Thread, Lock
import swifter
import dask
import dask.array as da
import dask.dataframe as dd
from dask.multiprocessing import get

from jinja2extension import FromJsonExtension

import ast

from gettime import popular_time
from attributes_analysis import get_common_attributes
#change1s
#import spacy
#from review_analysis import get_review_analysis
#change1e



app = Flask(__name__)
app.config['SECRET_KEY'] = sec_key
API_KEY_GEOCODE = geo_code

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'yelp_project_key.json'

client = bigquery.Client()

# Custom Jinja2 filter to convert JSON string to dictionary
def from_json_filter(value):
    # Replace single quotes with double quotes and load as Python literal
    value = value.replace("'", '"')
    return json.loads(value)

# Register the filter with Jinja2 environment
app.jinja_env.filters['from_json'] = from_json_filter

#variable initializations
category = ''
address = ''
distance = 0
lat = ''
long = ''
engine = ''
avg_start = []
avg_end = []
filtered_df = pd.DataFrame()
business_df = pd.DataFrame()
top10_df = pd.DataFrame()
bottom10_df = pd.DataFrame()
all_business_df = pd.DataFrame()
top_review_analysis_df = pd.DataFrame()
bottom_review_analysis_df = pd.DataFrame()
top_attributes = {}
bottom_attributes = {}
success_score = 0
percentage_positive_reviews = 0
first_time_fetch_flag = 0
filtered_empty_check_flag = 0




#getting coordinates from input address
def get_coordinates(address):

    global lat
    global long
    global API_KEY_GEOCODE
    #address = "3388 Gateway Blvd, Edmonton"
    url = f"https://api.geoapify.com/v1/geocode/search?text={address}&limit=1&apiKey={API_KEY_GEOCODE}"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        result = data["features"][0]

        lat = result["geometry"]["coordinates"][1]
        long = result["geometry"]["coordinates"][0]
        print(lat)
        print(long)

    else:
        print(f"Request failed with status code {response.status_code}")

def get_coordinates_static():
    global lat
    global long
    lat = 53.466884
    long = -113.492799

#distance calculation
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return round(distance, 2)

#fetch from module(debug it)
def fetch_all():
    global business_df
    #uncomment below to get data from sql
    #business_df = fetch_all_sql()
    business_df = fetch_all_json()
    print(business_df.head())

#@app.before_request
def fetch_all_csv():
    global business_df
    business_df = pd.read_csv('business_converted.csv')
    business_df['ratings'] = business_df['stars'] * business_df['review_count']

#@app.before_request
def fetch_all_sql():
    global business_df
    global client
    sql_query = """
    select * from yelp_dataset.yelp_academic_dataset_business
    """

    business_df = client.query(sql_query).to_dataframe()
    business_df['ratings'] = business_df['stars'] * business_df['review_count']

#@app.before_request
def fetch_all_json():
    global business_df
    data_file = open("yelp_academic_dataset_business.json")
    data = []
    for line in data_file:
        data.append(json.loads(line))
    business_df = pd.DataFrame(data)
    business_df['ratings'] = business_df['stars'] * business_df['review_count']
    data_file.close()


#just for trial, original function in reviews_analysis file
def get_reviews_sql(b_id):
    global engine
    engine = sq.create_engine(sql_engine)
    meta = MetaData(bind=engine)
    MetaData.reflect(meta)

    Session = sessionmaker(bind=engine)
    session = Session()

    #QUERY2 reviews
    REVIEWS = meta.tables['reviews']
    result_reviews = session.query(REVIEWS).filter(REVIEWS.business_id.in_(b_id))
    reviews_df = pd.DataFrame(result_reviews)

    #QUERY3 tips
    TIPS = meta.tables['tips']
    result_tips = session.query(TIPS).filter(TIPS.business_id.in_(b_id))
    tips_df = pd.DataFrame(result_tips)

    session.close()
    return reviews_df, tips_df

#new functions
def read_reviews():
    global top_review_analysis_df
    global bottom_review_analysis_df
    global percentage_positive_reviews
    #change2s
    top_review_analysis_df = pd.read_csv('top_review_analysis.csv')
    bottom_review_analysis_df = pd.read_csv('bottom_review_analysis.csv')
    #change2e
    top_review_analysis_df['sentiment'] = round(top_review_analysis_df['sentiment'], 1)
    bottom_review_analysis_df['sentiment'] = round(bottom_review_analysis_df['sentiment'], 1)
    #counting positive review count for success score
    total_review_count = top_review_analysis_df.shape[0] + bottom_review_analysis_df.shape[0]
    positive_review_count = (top_review_analysis_df[top_review_analysis_df['sentiment']>0.4].shape[0] +
                             bottom_review_analysis_df[bottom_review_analysis_df['sentiment']>0.4].shape[0])
    percentage_positive_reviews = (positive_review_count * 100) / total_review_count
    top_review_analysis_df = top_review_analysis_df[top_review_analysis_df['sentiment']>=0.7]
    bottom_review_analysis_df = bottom_review_analysis_df[bottom_review_analysis_df['sentiment']<=-0.4]
    #print('Top reviews shape: ', top_review_analysis_df.shape)
    #print('Bottom reviews shape: ', bottom_review_analysis_df.shape)
    top_review_analysis_df = get_review_keyword_count1(top_review_analysis_df)
    bottom_review_analysis_df = get_review_keyword_count1(bottom_review_analysis_df)
    top_review_analysis_df['sentence'] = top_review_analysis_df['sentence'].str.replace("'m"," am").str.replace("'ve"," have").str.replace("'","").str.replace(r'\n',' ', regex=True).str.strip()
    bottom_review_analysis_df['sentence'] = bottom_review_analysis_df['sentence'].str.replace("'m"," am").str.replace("'ve"," have").str.replace("'","").str.replace(r'\n',' ', regex=True).str.strip()


def get_review_keyword_count1(df):

    word_counts = df['feature'].value_counts().reset_index()
    word_counts.columns = ['feature', 'occurrences']
    df = df.merge(word_counts, on='feature')

    filtered_df = df[df['occurrences'] > 1]
    #filtered_df = df.copy()
    filtered_df = filtered_df.drop_duplicates(subset='feature', keep='first')
    filtered_df = filtered_df.sort_values(by='occurrences', ascending=False)

    #print(filtered_df)
    #filtered_df['sentiment_cat'] = pd.cut(filtered_df['sentiment'], [-1.0,-0.5,0.5,1.0], labels=['Negative','Neutral','Positive'])


    return filtered_df

#all filters go here
# instantiating the decorator
#@profile
def filter_data(category, address, distance):
    global filtered_df
    global lat
    global long
    global top10_df
    global bottom10_df
    global all_business_df
    global avg_start
    global avg_end
    global top_review_analysis_df
    global bottom_review_analysis_df
    global top_attributes
    global bottom_attributes
    global success_score
    global business_df
    global filtered_empty_check_flag

    if(address == 'empty' or distance == -1):
        filtered_df = business_df.copy()
    else:
        #uncomment below to get dynamic address coordinates
        get_coordinates(address)
        #get_coordinates_static()
        start = time.time()
        #business_df['distance'] = business_df.apply(lambda row: calculate_distance(row['latitude'], row['longitude'], lat, long), axis=1)
        business_map = dd.from_pandas(business_df, npartitions=30)
        business_df['distance'] = business_map.map_partitions(lambda df: df.apply(lambda row: calculate_distance(row['latitude'], row['longitude'], lat, long), axis=1)).compute(scheduler='processes')
        end = time.time()
        filtered_df = business_df[business_df['distance'] <= distance]
        if(filtered_df.shape[0] == 0):
            filtered_empty_check_flag = 1
            return redirect(url_for('home'))
    if(category != 'empty'):
        filtered_df = filtered_df[filtered_df['categories'].str.contains(category,na=False, case=False)]
    all_business_df = filtered_df.copy()

    #multiprocessing
    read_reviews()
    get_top_businesses()
    get_bottom_businesses()


#reviews, tips = get_reviews_sql(top10_df['business_id'].to_list())
    # Print extracted opinions
    #print("Extracted Opinions:")
    # for feature, sentence, sentiment in top_review_analysis:
    #     print(f"Feature: {feature}")
    #     print(f"Sentence: {sentence}")
    #     print(f"Sentiment: {sentiment}")
    #     print()

    #change5s
    #read_reviews()
    #change5e
    #common attributes


    #opening_mean = all_business_df['is_open'].mean()
    success_score = round(((all_business_df['is_open'].mean() * 100) +
                           ((all_business_df['stars'].mean() / 5) * 100) +
                           (percentage_positive_reviews)
                           ) / 3, 1)
    print("Execution inside filter: ",round(end-start, 2),"secs")
    return redirect(url_for('filtered'))

def get_top_businesses():
    start = time.time()
    global filtered_df
    global top10_df
    global top_review_analysis_df
    global top_attributes

    #top section
    top10_df = filtered_df.sort_values('ratings', ascending=False).iloc[0:10]
    top10_df['attributes'] = top10_df['attributes'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)
    avg_start, avg_end = popular_time(top10_df)
    #nlp review analysis
    #change3s
    #adding dask
    #dask_array = da.from_array(top10_df['business_id'].to_list(), chunks=30)
    #top_review_analysis = dask_array.map_partitions(get_review_analysis)

    # Compute the result and convert it back to a regular Python list
    #top_review_analysis = get_review_analysis(top10_df['business_id'].to_list())
    #change3e

    #top_review_analysis_df = pd.DataFrame(top_review_analysis, columns=['feature', 'sentence', 'sentiment'])
    #top_review_analysis_df.to_csv('top_review_analysis.csv')
    top_review_analysis_df = top_review_analysis_df[top_review_analysis_df['sentiment'] != 0].sort_values('sentiment', ascending=False)#.iloc[0:10]
    top_attributes = get_common_attributes(top10_df.dropna(subset=['attributes']))
    filtered_df = filtered_df[~filtered_df['business_id'].isin(top10_df['business_id'])]
    end = time.time()
    print("Execution top: ",round(end-start, 2),"secs")

def get_bottom_businesses():
    start = time.time()
    global filtered_df
    global bottom10_df
    global bottom_review_analysis_df
    global bottom_attributes

    #bottom section
    bottom10_df = filtered_df.sort_values('ratings').iloc[0:10]
    bottom10_df['attributes'] = bottom10_df['attributes'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)
    #change4s
    #adding dask
    #dask_array = da.from_array(bottom10_df['business_id'].to_list(), chunks=30)
    #bottom_review_analysis = dask_array.map_partitions(get_review_analysis)

    #bottom_review_analysis = get_review_analysis(bottom10_df['business_id'].to_list())
    #bottom_review_analysis_df = pd.DataFrame(bottom_review_analysis, columns=['feature', 'sentence', 'sentiment'])
    #change4e
    #bottom_review_analysis_df.to_csv('bottom_review_analysis.csv')
    bottom_review_analysis_df = bottom_review_analysis_df[bottom_review_analysis_df['sentiment'] != 0].sort_values('sentiment', ascending=True)#.iloc[0:10]
    bottom_attributes = get_common_attributes(bottom10_df.dropna(subset=['attributes']))
    filtered_df = filtered_df[~filtered_df['business_id'].isin(bottom10_df['business_id'])]
    end = time.time()
    print("Execution bottom: ",round(end-start, 2),"secs")

@app.route('/_autocomplete', methods=['GET'])
def autocomplete():
    unique_cities = pd.read_csv("unique_cities.csv")

    cities = unique_cities['city'].tolist()
    return Response(json.dumps(cities), mimetype='application/json')

@app.route('/_autocompletecategory', methods=['GET'])
def autocompletecategory():
    categories = ["Doctor",
              "Food",
              "Restaurant",
              "Automotive",
              "Shopping",
              "Real Estate",
              "Pet",
              "Hardware",
              "Hair",
              "Active Life",
              "Sports",
                  "Games",
                  "Gyms",
                  "Yoga",
                  "Fitness",
                  "Skating",
                  "Fishing",
                  "Bars",
                  "Coffee",
                  "Event Planning",
                  "Cafe",
                  "Arts",
                  "Pizza",
                  "Burger",
                  "Auto Repair",
                  "Bakery",
                  "Banks",
                  "Barbers",
                  "Spas",
                  "Bike Rentals",
                  "Body Shops",
                  "Boating",
                  "Books",
                  "Ice Cream",
                  "Fashion",
                  "Japanese",
                  "Italian",
                  "Korean",
                  "Grocery",
                  "Health",
                  "Medical",
                  "Home Services",
                  "Painters",
                  "Gas Stations",
                  "Apartments",
                  "Drugstores",
                  "Desserts",
                  "Travel",
                  "Sewing",
                  "Shoe Repair",
                  "Clothing",
                  "Car Wash",
                  "Education",
                  "Sandwiches",
                  "Eyewear",
                  "Watches",
                  "Jewelry",
                  "Music",
                  "Hotels",
                  "Indian",
                  "Veterinarians",
                  "Seafood"]
    return Response(json.dumps(categories), mimetype='application/json')

#flask routes


@app.route('/', methods=('GET', 'POST'))
def home():
    global category
    global address
    global distance
    global first_time_fetch_flag
    global filtered_empty_check_flag

    if request.method == 'GET':
        return render_template('home.html',
                               error_flag=filtered_empty_check_flag,
                               error_message="")
        print("GET")
    else:
        print("POST")
        if request.method == 'POST':
            if request.form['category']:
                category = request.form['category']
            else:
                category = 'empty'
            if request.form['address']:
                address = request.form['address']
            else:
                address = 'empty'
            if request.form['distance']:
                distance = float(request.form['distance'])
            else:
                distance = -1

        if not category:
            flash('Category is required!')
        else:
            if(first_time_fetch_flag == 0):
                fetch_all_csv()
                print("Business Fetched")
                first_time_fetch_flag = 1
            start = time.time()
            filter_data(category,address,distance)
            end = time.time()
            print("Execution time: ",round(end - start, 2),"secs")
            if(filtered_empty_check_flag == 0):
                print("Everything found")
                return redirect(url_for('filtered'))
            elif(filtered_empty_check_flag == 1):
                print("Address not found")
                filtered_empty_check_flag = 0
                return render_template('home.html',
                                       error_flag=1,
                                       error_message="No businesses found at the address.")

        return render_template('home.html',
                               error_flag=filtered_empty_check_flag,
                               error_message="")

@app.route('/filtered')
def filtered():
    global top10_df
    #top10_df['attributes'] = json.loads(top10_df['attributes'].replace("'", "\""))
    return render_template('filtered.html',
                           category=category,
                           address=address,
                           distance=distance,
                           filtered_businesses=filtered_df,
                           top_businesses=top10_df,
                           bottom_businesses=bottom10_df,
                           all_businesses=all_business_df,
                           avg_start=avg_start,
                           avg_end=avg_end,
                           top_reviews=top_review_analysis_df,
                           bottom_reviews=bottom_review_analysis_df,
                           top_attributes=top_attributes,
                           bottom_attributes=bottom_attributes,
                           success_score=success_score)

@app.route('/exp')
def exp():
    return render_template('exp.html')

@app.route('/hometemplate')
def hometemplate():
    return render_template('filtered-template.html')
    
if __name__ == "__main__":
    app.run(host='127.0.0.1',port=8080, debug=True)
