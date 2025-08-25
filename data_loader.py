# data_loader.py

import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import numpy as np

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the straight-line distance between two lat/lon points."""
    R = 6371.0
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
    
    # 1. Load and process location data
    try:
        locations_df = pd.read_csv('data/karaganda_sp_garage.csv')
        column_mapping = {
            locations_df.columns[0]: 'Service Point',
            locations_df.columns[1]: 'Latitude',
            locations_df.columns[2]: 'Longitude'
        }
        locations_df = locations_df.rename(columns=column_mapping)
        if locations_df['Latitude'].dtype == 'object':
            locations_df['Latitude'] = locations_df['Latitude'].str.replace(',', '.').astype(float)
        if locations_df['Longitude'].dtype == 'object':
            locations_df['Longitude'] = locations_df['Longitude'].str.replace(',', '.').astype(float)
        locations_df.dropna(subset=['Latitude', 'Longitude'], inplace=True)
        
        garage_location = locations_df.iloc[0]
        ecostation_locations = locations_df.iloc[1:].copy()
    except Exception as e:
        raise FileNotFoundError(f"Could not load or process 'data/karaganda_sp_garage.csv'. Error: {e}")

    # 2. Load and process outbound (collection) data
    try:
        outbound_df = pd.read_csv('data/f0386aadc6af4628b83914e8ec27d6c7.csv', delimiter=';')
    except Exception as e:
        raise FileNotFoundError(f"Could not load or process outbound data file. Error: {e}")

    outbound_df['Ecostation'] = outbound_df['Department / Facility'].str.split(' > ').str[1].str.strip()
    outbound_df['Creation Time'] = pd.to_datetime(outbound_df['Creation Time'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    outbound_df['Net Weight'] = pd.to_numeric(outbound_df['Net Weight'], errors='coerce').fillna(0)
    outbound_df.dropna(subset=['Creation Time'], inplace=True)
    
    # 3. Calculate station metrics (capacity, accumulation rate)
    collection_events = outbound_df.groupby(['Ecostation', 'Creation Time'])['Net Weight'].sum().reset_index()
    collection_events = collection_events.sort_values(by=['Ecostation', 'Creation Time'])

    station_analysis = []
    for station_name, station_data in collection_events.groupby('Ecostation'):
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
                    'Service Point': station_name,
                    'Max Capacity (kg)': max_capacity,
                    'Accumulation Rate (kg/day)': daily_rate
                })

    station_metrics = pd.DataFrame(station_analysis)
    
    # 4. Merge location and metric data
    ecostation_data = pd.merge(ecostation_locations, station_metrics, on='Service Point', how='left')
    avg_rate = station_metrics['Accumulation Rate (kg/day)'].mean()
    avg_capacity = station_metrics['Max Capacity (kg)'].mean()
    ecostation_data['Accumulation Rate (kg/day)'].fillna(avg_rate, inplace=True)
    ecostation_data['Max Capacity (kg)'].fillna(avg_capacity, inplace=True)

    # 5. Calculate Distance and Trip Duration Matrices
    points = pd.concat([garage_location.to_frame().T, ecostation_data])
    point_names = points['Service Point'].tolist()
    distance_matrix = pd.DataFrame(index=point_names, columns=point_names)
    trip_duration_matrix = pd.DataFrame(index=point_names, columns=point_names)

    for i, p1 in points.iterrows():
        for j, p2 in points.iterrows():
            distance = haversine(p1['Latitude'], p1['Longitude'], p2['Latitude'], p2['Longitude'])
            road_distance = distance * params['ROAD_NETWORK_FACTOR']
            travel_time_hours = road_distance / params['AVG_SPEED_KMH']
            
            distance_matrix.loc[p1['Service Point'], p2['Service Point']] = road_distance
            trip_duration_matrix.loc[p1['Service Point'], p2['Service Point']] = travel_time_hours

    # Calculate direct shipment trip times (Garage -> Station -> Garage)
    trip_times = {}
    for station_name in ecostation_data['Service Point']:
        travel_time_to_and_from = trip_duration_matrix.loc['Garage', station_name] * 2
        total_trip_hours = travel_time_to_and_from + (params['SERVICE_TIME_MIN'] / 60) + (params['UNLOADING_TIME_MIN'] / 60)
        trip_times[station_name] = total_trip_hours
        
    # **FIX**: Added 'garage_location' to the returned dictionary
    return {
        "ecostation_data": ecostation_data,
        "garage_location": garage_location,
        "trip_times": trip_times,
        "distance_matrix_km": distance_matrix.astype(float).round(2),
        "trip_duration_matrix_hours": trip_duration_matrix.astype(float).round(2)
    }
