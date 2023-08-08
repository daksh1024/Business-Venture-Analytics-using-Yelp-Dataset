import pandas as pd
import json
import sqlalchemy as sq
from sqlalchemy import create_engine, MetaData, \
    Table, Column, Numeric, Integer, VARCHAR, update, func
from sqlalchemy.orm import sessionmaker
from google.cloud import bigquery
import os


def fetch_all_json():
    business_df = pd.DataFrame()
    data_file = open("yelp_academic_dataset_business.json")
    data = []
    for line in data_file:
        data.append(json.loads(line))
    business_df = pd.DataFrame(data)
    business_df['ratings'] = business_df['stars'] * business_df['review_count']
    data_file.close()
    print(business_df.head())
    return business_df


def fetch_reviews(b_id):
    b_id_str = ", ".join(("'"+id_+"'") for id_ in b_id)
    sql_query = f"""
    select *
    from yelp_dataset.yelp_academic_dataset_review
    where business_id in ({b_id_str})
    """
    reviews_df = client.query(sql_query).to_dataframe()

    sql_query = f"""
    select *
    from yelp_dataset.yelp_academic_dataset_tip
    where business_id in ({b_id_str})
    """
    tips_df = client.query(sql_query).to_dataframe()

    return reviews_df, tips_df