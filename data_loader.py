# data_loader.py

import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the straight-line distance between two lat/lon points."""
    R = 6371.0  # Radius of Earth in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

def load_and_prepare_data(params):
    """
    Loads all data files, cleans them, and performs all pre-calculations 
    needed for the simulation and dashboard display.
    """
    
    # 1. Load and process location data from the new file
    try:
        # UPDATED FILENAME
        locations_df = pd.read_csv('data/karaganda_sp_garage.csv') 
        # The user specified "SP Name" is the column to be used for mapping.
        # We rename it to a standard name 'Service Point' for consistency.
        column_mapping = {
            'SP Name': 'Service Point',
            'Latitude': 'Latitude',
            'Longtitude': 'Longitude' # Correcting potential typo
        }
        # Check for Longitude typo
        if 'Longitude' not in locations_df.columns and 'Longtitude' in locations_df.columns:
             locations_df.rename(columns={'Longtitude': 'Longitude'}, inplace=True)

        locations_df = locations_df[['SP Name', 'Latitude', 'Longitude']].rename(columns={'SP Name': 'Service Point'})

        if locations_df['Latitude'].dtype == 'object':
            locations_df['Latitude'] = locations_df['Latitude'].str.replace(',', '.').astype(float)
        if locations_df['Longitude'].dtype == 'object':
            locations_df['Longitude'] = locations_df['Longitude'].str.replace(',', '.').astype(float)
        locations_df.dropna(subset=['Latitude', 'Longitude'], inplace=True)
        
        garage_location = locations_df[locations_df['Service Point'] == 'Garage'].iloc[0]
        ecostation_locations = locations_df[locations_df['Service Point'] != 'Garage'].copy()
    except Exception as e:
        raise FileNotFoundError(f"Could not load or process 'data/karaganda_sp_garage.csv'. Error: {e}")

    # 2. Load and process outbound (collection) data from the new file
    try:
        # UPDATED FILENAME
        outbound_df = pd.read_csv('data/karaganda_outbound.csv')
    except Exception as e:
        raise FileNotFoundError(f"Could not load or process 'data/karaganda_outbound.csv'. Error: {e}")

    outbound_df['Ecostation_Cyrillic'] = outbound_df['Department / Facility'].str.split(' > ').str[1].str.strip()
    outbound_df['Creation Time'] = pd.to_datetime(outbound_df['Creation Time'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    outbound_df['Net Weight'] = pd.to_numeric(outbound_df['Net Weight'], errors='coerce').fillna(0)
    outbound_df.dropna(subset=['Creation Time', 'Ecostation_Cyrillic'], inplace=True)
    
    # 3. Calculate station metrics (capacity, accumulation rate)
    collection_events = outbound_df.groupby(['Ecostation_Cyrillic', 'Creation Time'])['Net Weight'].sum().reset_index()
    collection_events = collection_events.sort_values(by=['Ecostation_Cyrillic', 'Creation Time'])

    station_analysis = []
    for station_name, station_data in collection_events.groupby('Ecostation_Cyrillic'):
        if len(station_data) > 1:
            time_diffs = station_data['Creation Time'].diff().dt.total_seconds() / (24 * 3600)
            avg_collection_kg = station_data['Net Weight'][station_data['Net Weight'] > 10].mean()
            if pd.isna(avg_collection_kg) or avg_collection_kg == 0: continue
            max_capacity = avg_collection_kg / params['CAPACITY_TRIGGER_PERCENT']
            weights = station_data['Net Weight'].iloc[1:]
            periods = time_diffs.iloc[1:]
            valid_periods = periods[periods > 0.5]
            valid_weights = weights[periods > 0.5]
            daily_rate = (valid_weights / valid_periods).mean() if not valid_periods.empty else 0
            if daily_rate > 0 and not np.isnan(daily_rate):
                 station_analysis.append({
                    'Ecostation_Cyrillic': station_name,
                    'Max Capacity (kg)': max_capacity,
                    'Accumulation Rate (kg/day)': daily_rate
                })
    station_metrics = pd.DataFrame(station_analysis)
    
    # 4. Map Cyrillic names from outbound data to Latin names from location data
    name_mapping = {
        'СОРТИРОВКА': 'Sortirovka', 'КАЙРАТ': 'Kairat', 'ПРИШАХТИНСК': 'Prishakhtinsk',
        'АЛИХАНОВА': 'Alihanova', 'ШАХТИНСК 2 биг бега': 'Shakhtinsk', 'ГОРНЯ
