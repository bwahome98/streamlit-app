import streamlit as st
import os
import re
import datetime
from operator import itemgetter
from googleapiclient.discovery import build
from google.auth import exceptions
from google.oauth2 import service_account

# Google Sheets details
SPREADSHEET_ID = '1qhm1d8nUyckL5PIApqwOclg4JtzJD3j3bArWKabaGcg'
RANGE_NAME = 'PRIORITY!A1:B1000'

# Streamlit app configuration
st.set_page_config(page_title="TATU CITY TRANSPORT", layout="centered", initial_sidebar_state="auto")

# Set UI styling
st.markdown("""
    <style>
        .stApp {
            background-color: black;
        }
        h1 {
            color: white;
            text-align: center;
            font-size: 32px;
        }
        .block-container {
            color: white;
            font-size: 12px;
        }
        .refresh-button {
            display: flex;
            justify-content: center;
            margin-top: 20px;
        }
        .stButton button {
            color: white;
            background-color: #333333;
        }
    </style>
""", unsafe_allow_html=True)

st.title('TATU CITY TRANSPORT')
st.subheader('Ranked Destinations & Potential Revenue')

# Global variable to keep track of total potential revenue
total_revenue = 0

# Authenticate using a service account
@st.cache_data
def authenticate_service_account():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        return credentials
    except exceptions.DefaultCredentialsError as e:
        st.error(f"Authentication error: {e}")
        raise

# Extract price from destination format
def extract_price_from_destination(destination):
    match = re.search(r"\((\d+)\s*KSH\)", destination, re.IGNORECASE)
    if match:
        price = int(match.group(1))
        return price
    return 0

# Check if timestamp falls within given hourly range
def is_within_hour_range(timestamp_str, start_hour, end_hour):
    timestamp = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
    if start_hour <= timestamp.hour < end_hour:
        return True
    return False

# Pull and rank data by the hourly range
def pull_and_rank_data_by_hour(start_hour, end_hour):
    global total_revenue
    creds = authenticate_service_account()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        return

    if not values or len(values) < 2:
        st.warning("No data found or not enough data.")
        return

    passenger_counts = {}
    destination_prices = {}
    hourly_revenue = 0

    for row in values[1:]:
        if len(row) < 2:
            continue
        
        timestamp_str, destination = row[0], row[1]

        if is_within_hour_range(timestamp_str, start_hour, end_hour):
            price = extract_price_from_destination(destination)
            clean_dest = re.sub(r" \(\d+KSH\)", "", destination)

            passenger_counts[clean_dest] = passenger_counts.get(clean_dest, 0) + 1
            destination_prices[clean_dest] = price

    ranked_destinations = sorted(passenger_counts.items(), key=itemgetter(1), reverse=True)

    st.markdown(f"### {start_hour}:00 - {end_hour}:00 Ranking")
    for rank, (destination, count) in enumerate(ranked_destinations, start=1):
        price = destination_prices.get(destination, 0)
        revenue_for_destination = count * price
        hourly_revenue += revenue_for_destination
        st.markdown(f"{rank}. {destination}: {count} passengers, Potential Revenue: {revenue_for_destination} KSH")

    st.markdown(f"**Hourly Potential Revenue**: {hourly_revenue} KSH")
    total_revenue += hourly_revenue

    return ranked_destinations

# Run hourly updates for the intervals between 11 PM and 7 AM
def run_hourly_updates():
    hourly_intervals = [
        (23, 0),  # 11 PM - 12 AM
        (0, 1),   # 12 AM - 1 AM
        (1, 2),   # 1 AM - 2 AM
        (2, 3),   # 2 AM - 3 AM
        (3, 4),   # 3 AM - 4 AM
        (4, 5),   # 4 AM - 5 AM
        (5, 6),   # 5 AM - 6 AM
        (6, 7),   # 6 AM - 7 AM
    ]
    
    for start_hour, end_hour in hourly_intervals:
        pull_and_rank_data_by_hour(start_hour, end_hour)

    st.markdown(f"**Potential Total Revenue for the Day**: {total_revenue} KSH")

# Refresh button to fetch and rank data
if st.button('Refresh', key='refresh'):
    total_revenue = 0
    run_hourly_updates() 


