#imports
from flask import Flask, render_template, request, url_for, flash, redirect, Response
from wtforms import StringField, Form
import json
from google.cloud import bigquery
import os
import pandas as pd
import numpy as np
import requests
from statistics import mean
from credentials import sql_engine, geo_code, sec_key, bigquery_cred
import sqlalchemy as sq
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData, \
    Table, Column, Numeric, Integer, VARCHAR, update, func
from math import radians, sin, cos, sqrt, atan2
from jinja2extension import FromJsonExtension
import simplejson as j
import ast
from gettime import popular_time
from attributes_analysis import get_common_attributes
#import spacy
#from review_analysis import get_review_analysis



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
top_review_analysis = []
bottom_review_analysis = []
top_attributes = {}
bottom_attributes = {}
success_score = 0
top_reviews_analysis_df = pd.DataFrame()
bottom_reviews_analysis_df = pd.DataFrame()
percentage_positive_reviews = 0
error = ''




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
def read_reviews_csv():
    global top_reviews_analysis_df
    global bottom_reviews_analysis_df
    global percentage_positive_reviews
    top_reviews_analysis_df = pd.read_csv('top_review_analysis.csv')
    bottom_reviews_analysis_df = pd.read_csv('bottom_review_analysis.csv')
    top_reviews_analysis_df['sentiment'] = round(top_reviews_analysis_df['sentiment'], 1)
    bottom_reviews_analysis_df['sentiment'] = round(bottom_reviews_analysis_df['sentiment'], 1)
    #counting positive review count for success score
    total_review_count = top_reviews_analysis_df.shape[0] + bottom_reviews_analysis_df.shape[0]
    positive_review_count = (top_reviews_analysis_df[top_reviews_analysis_df['sentiment']>0.4].shape[0] +
                             bottom_reviews_analysis_df[bottom_reviews_analysis_df['sentiment']>0.4].shape[0])
    percentage_positive_reviews = (positive_review_count * 100) / total_review_count
    top_reviews_analysis_df = top_reviews_analysis_df[top_reviews_analysis_df['sentiment']>=0.9]
    bottom_reviews_analysis_df = bottom_reviews_analysis_df[bottom_reviews_analysis_df['sentiment']<=-0.7]
    top_reviews_analysis_df = get_review_keyword_count1(top_reviews_analysis_df)
    bottom_reviews_analysis_df = get_review_keyword_count1(bottom_reviews_analysis_df)
    top_reviews_analysis_df['sentence'] = top_reviews_analysis_df['sentence'].str.replace("'m"," am").str.replace("'ve"," have").str.replace("'","").str.replace(r'\n',' ', regex=True).str.strip()
    bottom_reviews_analysis_df['sentence'] = bottom_reviews_analysis_df['sentence'].str.replace("'m"," am").str.replace("'ve"," have").str.replace("'","").str.replace(r'\n',' ', regex=True).str.strip()


def get_review_keyword_count1(df):

    word_counts = df['feature'].value_counts().reset_index()
    word_counts.columns = ['feature', 'occurrences']
    df = df.merge(word_counts, on='feature')
    filtered_df = df[df['occurrences'] > 1]
    filtered_df = filtered_df.drop_duplicates(subset='feature', keep='first')
    filtered_df = filtered_df.sort_values(by='occurrences', ascending=False)

    print(filtered_df)
    #filtered_df['sentiment_cat'] = pd.cut(filtered_df['sentiment'], [-1.0,-0.5,0.5,1.0], labels=['Negative','Neutral','Positive'])


    return filtered_df

def get_review_keyword_count2(df):

    word_counts = df['sentiment'].value_counts()

    # Find the maximum count
    max_count = word_counts.max()

    # Filter the words with the highest occurrences
    highest_occurrence_words = word_counts[word_counts == max_count].index

    # Filter the original DataFrame to keep only the rows with the highest occurrences
    filtered_df = df[df['sentiment'].isin(highest_occurrence_words)]

    return filtered_df

#all filters go here
def filter_data(category, address, distance):
    global filtered_df
    global lat
    global long
    global top10_df
    global bottom10_df
    global all_business_df
    global avg_start
    global avg_end
    global top_review_analysis
    global bottom_review_analysis
    global top_attributes
    global bottom_attributes
    global success_score
    global business_df
    global error


    if(address == 'empty' or distance == -1):
        filtered_df = business_df.copy()
    else:
        #uncomment below to get dynamic address coordinates
        get_coordinates(address)
        #get_coordinates_static()
        business_df['distance'] = business_df.apply(lambda row: calculate_distance(row['latitude'], row['longitude'], lat, long), axis=1)
        filtered_df = business_df[business_df['distance'] <= distance]
    if(category != 'empty'):
        filtered_df = filtered_df[filtered_df['categories'].str.contains(category,na=False, case=False)]
    all_business_df = filtered_df.copy()
    top10_df = filtered_df.sort_values('ratings', ascending=False).iloc[0:10]
    bottom10_df = filtered_df.sort_values('ratings').iloc[0:10]
    top10_df['attributes'] = top10_df['attributes'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)
    bottom10_df['attributes'] = bottom10_df['attributes'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)
    avg_start, avg_end = popular_time(top10_df)

    #nlp review analysis
    #top_review_analysis = get_review_analysis(top10_df['business_id'].to_list())
    #bottom_review_analysis = get_review_analysis(bottom10_df['business_id'].to_list())
    #reviews, tips = get_reviews_sql(top10_df['business_id'].to_list())
    # Print extracted opinions
    #print("Extracted Opinions:")
    #for feature, sentence, sentiment in top_review_analysis:
    #    print(f"Feature: {feature}")
    #    print(f"Sentence: {sentence}")
    #    print(f"Sentiment: {sentiment}")
    #    print()

    read_reviews_csv()

    #common attributes
    top_attributes = get_common_attributes(top10_df.dropna(subset=['attributes']))
    bottom_attributes = get_common_attributes(bottom10_df.dropna(subset=['attributes']))



    filtered_df = filtered_df[~filtered_df['business_id'].isin(top10_df['business_id'])]
    filtered_df = filtered_df[~filtered_df['business_id'].isin(bottom10_df['business_id'])]

    #opening_mean = all_business_df['is_open'].mean()

    #change this formula to accomodate +ve sentiment count
    success_score = round(((all_business_df['is_open'].mean()*100) +
                           ((all_business_df['stars'].mean()/5)*100) +
                           (percentage_positive_reviews)
                           ) / 3, 1)
    return redirect(url_for('filtered'))

#flask routes
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
                  "Car Wash"
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

@app.route('/error')
def error():
    global error
    return render_template('home.html', error=error)

@app.route('/', methods=('GET', 'POST'))
def home():
    global category
    global address
    global distance
    global error

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
        fetch_all_csv()
        #print(business_df.head())
        filter_data(category,address,distance)
        return redirect(url_for('filtered'))

    return render_template('home.html')

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
                           top_reviews=top_reviews_analysis_df,
                           bottom_reviews=bottom_reviews_analysis_df,
                           top_attributes=top_attributes,
                           bottom_attributes=bottom_attributes,
                           success_score=success_score)

@app.route('/exp')
def exp():
    return render_template('exp.html')

@app.route('/hometemplate')
def hometemplate():
    return render_template('filtered-template.html')