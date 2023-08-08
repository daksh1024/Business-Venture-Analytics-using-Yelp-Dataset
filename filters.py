from math import radians, sin, cos, sqrt, atan2
import pandas as pd
import requests


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

    else:
        print(f"Request failed with status code {response.status_code}")

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