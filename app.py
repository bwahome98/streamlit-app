import streamlit as st
import re
import datetime
from operator import itemgetter
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Custom CSS for styling
st.markdown("""
    <style>
    body {
        background-color: black;
    }
    .title-container {
        font-size: 16px;
        border: 1px solid white;
        padding: 10px;
        margin-bottom: 10px;
        color: white;
    }
    .content-container {
        font-size: 12px;
        color: white;
    }
    .stButton button {
        width: 100%;
        font-size: 14px;
    }
    h1 {
        text-align: center;
        color: white;
        font-size: 24px;
    }

    /* Ensuring the black background applies across all elements */
    .main {
        background-color: black !important;
    }
    
    /* Custom column layout */
    .stContainer > div {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        padding: 10px;
        border-bottom: 1px solid white;
    }
    .stContainer > div > div {
        width: 33%;
        text-align: left;
    }

    /* Mobile styles */
    @media only screen and (max-width: 600px) {
        .title-container {
            font-size: 14px;
            padding: 8px;
        }
        .content-container {
            font-size: 10px;
        }
        h1 {
            font-size: 20px;
        }
        .stButton button {
            font-size: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Your Google Sheets spreadsheet details
SPREADSHEET_ID = '1qhm1d8nUyckL5PIApqwOclg4JtzJD3j3bArWKabaGcg'
RANGE_NAME = 'PRIORITY!A1:B1000'

total_revenue = 0

def authenticate_service_account():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        return credentials
    except Exception as e:
        st.error(f"Error in authentication: {e}")
        raise

def extract_price_from_destination(destination):
    match = re.search(r"\((\d+)\s*KSH\)", destination, re.IGNORECASE)
    if match:
        price = int(match.group(1))
        return price
    return 0

def is_within_hour_range(timestamp_str, start_hour, end_hour):
    timestamp = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
    return start_hour <= timestamp.hour < end_hour

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

    # Display ranking with responsive columns
    st.markdown(f"<div class='title-container'>Current Ranking of Destinations for {start_hour}:00 - {end_hour}:00 by Passenger Count:</div>", unsafe_allow_html=True)
    
    for rank, (destination, count) in enumerate(ranked_destinations, start=1):
        price = destination_prices.get(destination, 0)
        revenue_for_destination = count * price
        hourly_revenue += revenue_for_destination

        st.markdown(
            f"""
            <div>
                <div>{rank}. {destination}</div>
                <div>{count} passengers</div>
                <div>Revenue: {revenue_for_destination} KSH</div>
            </div>
            """, unsafe_allow_html=True
        )

    st.write(f"Potential Total Revenue for {start_hour}:00 - {end_hour}:00: {hourly_revenue} KSH", unsafe_allow_html=True)

    total_revenue += hourly_revenue
    return ranked_destinations

def run_hourly_updates():
    global total_revenue
    total_revenue = 0

    hourly_intervals = [
        (23, 0),
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (6, 7),
    ]
    
    for start_hour, end_hour in hourly_intervals:
        pull_and_rank_data_by_hour(start_hour, end_hour)

    st.write(f"\nPotential Total Revenue for the Day: {total_revenue} KSH", unsafe_allow_html=True)

# Page heading
st.markdown("<h1>TATU CITY TRANSPORT</h1>", unsafe_allow_html=True)

# Refresh button at the top
if st.button('Refresh Data'):
    st.write("Fetching and ranking data...")
    run_hourly_updates()
