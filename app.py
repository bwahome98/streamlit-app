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
        /* Stack the columns vertically on mobile */
        .block-container .stColumns {
            display: block;
        }
        .block-container .stColumns > div {
            width: 100% !important;
            margin-bottom: 10px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Your Google Sheets spreadsheet details
SPREADSHEET_ID = '1qhm1d8nUyckL5PIApqwOclg4JtzJD3j3bArWKabaGcg'
RANGE_NAME = 'PRIORITY!A1:B1000'

total_revenue = 0

# Authentication using a service account
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

# Extract the price from the destination string (e.g., "Destination (500KSH)")
def extract_price_from_destination(destination):
    match = re.search(r"\((\d+)\s*KSH\)", destination, re.IGNORECASE)
    if match:
        price = int(match.group(1))
        return price
    return 0

# Check if the timestamp falls within the given hourly range
def is_within_hour_range(timestamp_str, start_hour, end_hour):
    timestamp = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
    return start_hour <= timestamp.hour < end_hour

# Pull and rank data from Google Sheets, calculate potential revenue
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

    # Start processing rows (skip the header row)
    for row in values[1:]:
        if len(row) < 2:
            continue  # Skip incomplete rows

        timestamp_str, destination = row[0], row[1]

        # Filter data by the given hourly range (e.g., 11 PM to 12 AM)
        if is_within_hour_range(timestamp_str, start_hour, end_hour):
            # Extract price from the destination string
            price = extract_price_from_destination(destination)

            # Clean the destination name by removing the price part (e.g., "Destination (Price)")
            clean_dest = re.sub(r" \(\d+KSH\)", "", destination)

            passenger_counts[clean_dest] = passenger_counts.get(clean_dest, 0) + 1
            destination_prices[clean_dest] = price

    # Rank destinations by passenger count
    ranked_destinations = sorted(passenger_counts.items(), key=itemgetter(1), reverse=True)

    # Display ranking with responsive columns
    st.markdown(f"<div class='title-container'>Current Ranking of Destinations for {start_hour}:00 - {end_hour}:00 by Passenger Count:</div>", unsafe_allow_html=True)
    
    # Define custom column headers
    headers = ['Rank', 'Destination', 'Number of passengers', 'Potential revenue']
    
    # Create table data
    table_data = [headers]  # Add headers first
    for rank, (destination, count) in enumerate(ranked_destinations, start=1):
        price = destination_prices.get(destination, 0)
        revenue_for_destination = count * price
        hourly_revenue += revenue_for_destination
        table_data.append([rank, destination, count, f"{revenue_for_destination} KSH"])

    # Display data as a table without the index
    st.table(table_data)

    st.write(f"Potential Total Revenue for {start_hour}:00 - {end_hour}:00: {hourly_revenue} KSH", unsafe_allow_html=True)

    total_revenue += hourly_revenue
    return ranked_destinations

# Run the function for each hourly interval between 11 PM and 6 AM
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
