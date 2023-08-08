# Uploading necessary libraries
import pandas as pd
import sqlalchemy as sq
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData, \
    Table, Column, Numeric, Integer, VARCHAR, update, func
import spacy
from collections import Counter
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
from credentials import sql_engine
from google.cloud import bigquery
import os

nltk.download('punkt')
nlp = spacy.load("en_core_web_sm")
nltk.download('vader_lexicon')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'yelp_project_key.json'
client = bigquery.Client()


def get_reviews_csv(b_id):
    reviews_df = pd.read_csv('business_reviews_subset.csv')
    tips_df = pd.read_csv('tips_converted.csv')
    reviews_df = reviews_df[reviews_df['business_id'].isin(b_id)]
    tips_df = tips_df[tips_df['business_id'].isin(b_id)]

    return reviews_df, tips_df

def fetch_reviews(b_id):
    global client
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

# Function to preprocess texts of reviews
def preprocess_text(text):
    global nlp;
    doc = nlp(text)
    processed_text = [token.lemma_.lower() for token in doc if not token.is_stop and token.pos_ == 'NOUN' and not token.is_punct and not token.like_num and token.lemma_.lower() not in custom_stop_words]
    return processed_text

# Function to extract opinions using SpaCy for sentiment analysis
def extract_opinions(text, selected_features_set):
    global nlp;
    opinions = []
    sid = SentimentIntensityAnalyzer()
    doc = nlp(text)

    for sentence in doc.sents:
        sentiment_scores = sid.polarity_scores(sentence.text) # Calculates sentiment scores for each sentence
        sentiment = sentiment_scores['compound'] # Compound score is used (positive closer to +1, negative closer to -1, neutral closer to 0)

        for token in sentence:
            if (token.text.lower() in selected_features_set or token.lemma_.lower() in selected_features_set) and token.pos_ == 'NOUN':
                selected_feature = token.text.lower() if token.text.lower() in selected_features_set else token.lemma_.lower()

                sentiment_words = []
                for child in token.children:
                    if child.pos_ in ['ADJ', 'VERB']:
                        sentiment_words.append(child.text)

                        # Early stopping: If sentiment-bearing word found, break the loop
                        break

                if sentiment_words:
                    # Check for negation using dependency parsing
                    for child in token.children:
                        if child.text.lower() in ["not", "n't", "never", "no"]:
                            sentiment *= -1
                            break

                # Append the opinion with the singular form of the word from selected_features_set
                opinions.append((selected_feature, sentence.text, sentiment))

    return opinions

def get_review_analysis(b_id):

    #change below function call from csv to sql when production
    #reviews_df, tips_df = fetch_reviews(b_id)
    reviews_df, tips_df = get_reviews_csv(b_id)

    corpus = reviews_df['text'].tolist() + tips_df['text'].tolist()
    custom_stop_words = {'bit', 'lot', 'time', 'items', 'way', 'people', 'person', 'pm', 'am', 'one', 'thing', 'today', 'tomorrow', 'yesterday'}

    processed_corpus = [preprocess_text(text) for text in corpus]
    flat_corpus = [word for sublist in processed_corpus for word in sublist]

    word_freq = Counter(flat_corpus)
    num_words_min_frequency = 2
    selected_features_set = {word for word, freq in word_freq.items() if freq >= num_words_min_frequency}
    sorted_selected_features = sorted(selected_features_set, key=lambda word: word_freq[word], reverse=True)

    sorted_features_proportion = len(sorted_selected_features) // 2
    selected_features_set = sorted_selected_features[:sorted_features_proportion]

    # Apply opinion extraction on each review
    extracted_opinions = []
    for i, text in enumerate(corpus):
        opinions = extract_opinions(text, selected_features_set)
        extracted_opinions.extend(opinions)

    return extracted_opinions