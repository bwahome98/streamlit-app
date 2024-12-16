import streamlit as st
import os
import re
import datetime
from operator import itemgetter
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth import exceptions
from google.oauth2 import service_account

# Your Google Sheets spreadsheet details
SPREADSHEET_ID = '1qhm1d8nUyckL5PIApqwOclg4JtzJD3j3bArWKabaGcg'  # Replace with your actual spreadsheet ID
RANGE_NAME = 'PRIORITY!A1:B1000'  # Adjust to the actual range that captures both timestamp and destination

# Path to your service account credentials JSON file
json_file_path = 'C:/Users/USER/Documents/TRANSPORT BACKEND/credentials.json'

# Global variable to keep track of potential total revenue for the day
total_revenue = 0

def authenticate_service_account(json_file_path):
    """Authenticate using a service account."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            json_file_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        return credentials
    except exceptions.DefaultCredentialsError as e:
        st.error(f"Error in authentication: {e}")
        raise

def extract_price_from_destination(destination):
    """Extract the price from the format 'Destination (Price)'."""
    match = re.search(r"\((\d+)\s*KSH\)", destination, re.IGNORECASE)
    if match:
        price = int(match.group(1))  # Extract the price in KSH
        return price
    return 0  # Return 0 if no price found

def is_within_hour_range(timestamp_str, start_hour, end_hour):
    """Check if the timestamp falls within the given hourly range."""
    timestamp = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')

    if start_hour <= timestamp.hour < end_hour:
        return True
    return False

def pull_and_rank_data_by_hour(start_hour, end_hour):
    """Pull data from Google Sheets, filter by specific hourly range, clean, and rank destinations."""
    global total_revenue
    creds = authenticate_service_account(json_file_path)
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
            continue  # Skip any incomplete rows

        timestamp_str, destination = row[0], row[1]

        if is_within_hour_range(timestamp_str, start_hour, end_hour):
            price = extract_price_from_destination(destination)
            clean_dest = re.sub(r" \(\d+KSH\)", "", destination)

            passenger_counts[clean_dest] = passenger_counts.get(clean_dest, 0) + 1
            destination_prices[clean_dest] = price

    ranked_destinations = sorted(passenger_counts.items(), key=itemgetter(1), reverse=True)

    st.write(f"\nCurrent Ranking of Destinations for {start_hour}:00 - {end_hour}:00 by Passenger Count:")
    for rank, (destination, count) in enumerate(ranked_destinations, start=1):
        price = destination_prices.get(destination, 0)
        revenue_for_destination = count * price
        hourly_revenue += revenue_for_destination
        st.write(f"{rank}. {destination}: {count} passengers, Potential Revenue: {revenue_for_destination} KSH")

    st.write(f"Potential Total Revenue for {start_hour}:00 - {end_hour}:00: {hourly_revenue} KSH")

    total_revenue += hourly_revenue

    return ranked_destinations

def run_hourly_updates():
    global total_revenue
    total_revenue = 0  # Reset the total revenue each time the refresh button is clicked

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

    st.write(f"\nPotential Total Revenue for the Day: {total_revenue} KSH")

# Streamlit button for refreshing data
if st.button('Refresh Data'):
    st.write("Fetching and ranking data...")
    run_hourly_updates()

