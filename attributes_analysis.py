import pandas as pd
from collections import Counter
import ast


def get_common_attributes(df):

    #df['attributes'] = df['attributes'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else x)

    common_counter = Counter()

    for dictionary in df['attributes']:
        common_counter.update(dictionary.items())

    filtered_pairs = {pair: count for pair, count in common_counter.items() if count > 1}
    sorted_pairs = dict(sorted(filtered_pairs.keys(), key=lambda x: filtered_pairs[x], reverse=True))

    return sorted_pairs

