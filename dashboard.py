# dashboard.py

import streamlit as st
import pandas as pd
import numpy as np

# Import the functions and variables from our other project files
from config import DEFAULT_PARAMS
from data_loader import load_and_prepare_data
from simulation import run_simulation

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Evraka | Operations Capacity Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SIDEBAR - CONFIGURABLE PARAMETERS ---
st.sidebar.title("Simulation Parameters")
st.sidebar.write("Adjust the parameters below to model different operational scenarios.")

params = {}
params['NUM_TRUCKS'] = DEFAULT_PARAMS['NUM_TRUCKS']
params['DAILY_WORK_HOURS'] = st.sidebar.slider("Daily Work Hours per Truck", 4.0, 12.0, DEFAULT_PARAMS['DAILY_WORK_HOURS'], 0.5)
params['ECOSTATION_WORK_HOURS'] = st.sidebar.slider("Ecostation Work Hours (for accumulation)", 4.0, 12.0, DEFAULT_PARAMS['ECOSTATION_WORK_HOURS'], 0.5)
params['AVG_SPEED_KMH'] = st.sidebar.slider("Average Truck Speed (km/h)", 20.0, 60.0, DEFAULT_PARAMS['AVG_SPEED_KMH'], 1.0)
params['SERVICE_TIME_MIN'] = st.sidebar.slider("Service Time per Ecostation (min)", 10.0, 60.0, DEFAULT_PARAMS['SERVICE_TIME_MIN'], 5.0)
params['UNLOADING_TIME_MIN'] = st.sidebar.slider("Unloading Time at Garage (min)", 15.0, 90.0, DEFAULT_PARAMS['UNLOADING_TIME_MIN'], 5.0)
params['ROAD_NETWORK_FACTOR'] = st.sidebar.slider("Road Network Factor (1.0 = Straight Line)", 1.0, 2.0, DEFAULT_PARAMS['ROAD_NETWORK_FACTOR'], 0.05)
params['CAPACITY_TRIGGER_PERCENT'] = st.sidebar.slider("Collection Trigger at Capacity (%)", 0.60, 1.0, DEFAULT_PARAMS['CAPACITY_TRIGGER_PERCENT'], 0.05)
params['SIMULATION_DAYS'] = DEFAULT_PARAMS['SIMULATION_DAYS']

# --- 3. MAIN APPLICATION ---
st.title("Karaganda Ecostation Operations Analysis")
st.markdown(f"A simulation of the current **{params['NUM_TRUCKS']} truck fleet** over a **{params['SIMULATION_DAYS']}-day period** based on historical data.")

if st.sidebar.button("▶️ Run Analysis", type="primary", use_container_width=True):

    with st.spinner("Preparing data and running simulation... Please wait."):
        try:
            # Step 1: Load and prepare all data based on sidebar parameters
            prepared_data = load_and_prepare_data(params)
            num_existing_stations = 12

            # Step 2: Run the simulation for the current state
            results = run_simulation(
                station_data=prepared_data['ecostation_data'].head(num_existing_stations),
                trip_times=prepared_data['trip_times'],
                params=params
            )
            
            # --- 4. DASHBOARD TABS (FRONTEND / BACKEND) ---
            summary_tab, data_tab = st.tabs(["📊 Executive Summary", "🗂️ Detailed Data & Matrices"])

            with summary_tab:
                st.header("Current State Analysis (12 Ecostations)")

                # --- KPI Metrics ---
                col1, col2, col3 = st.columns(3)
                col1.metric("Fleet Utilization", f"{results['utilization_percent']:.1f}%",
                            help="The percentage of total available working hours that trucks spent actively on trips (driving, servicing, unloading).")
                
                col2.metric("Service Failures (Overflows)", f"{results['service_failures']}",
                            help="The number of times an ecostation's capacity exceeded 100% before a truck could arrive for collection.")

                col3.metric(f"Total Trips ({params['SIMULATION_DAYS']} days)", f"{results['total_trips']}")

                # --- Main Verdict ---
                st.subheader("Verdict")
                failure_rate = (results['service_failures'] / results['total_trips']) * 100 if results['total_trips'] > 0 else 0
                
                if failure_rate > 3.0 or results['service_failures'] > (num_existing_stations * 0.25):
                    st.error(f"""
                    **System Capacity Exceeded:** The simulation indicates that the current fleet of **{params['NUM_TRUCKS']} trucks is INSUFFICIENT** for the existing 12 ecostations under the 'direct shipment' model.
                    - **{results['service_failures']} overflow events** were recorded, meaning stations are frequently unserviced before they become overfilled.
                    - With a high utilization rate of **{results['utilization_percent']:.1f}%**, the fleet has no spare capacity to handle delays or additional workload.
                    """)
                else:
                    st.success(f"""
                    **System Capacity Sufficient:** The simulation indicates that the current fleet of **{params['NUM_TRUCKS']} trucks is SUFFICIENT** for the 12 ecostations.
                    - Only **{results['service_failures']} overflow events** were recorded, which is within an acceptable operational tolerance.
                    - The fleet utilization of **{results['utilization_percent']:.1f}%** suggests there is remaining capacity in the system.
                    """)

                # --- Visualizations ---
                st.subheader("Visual Analysis")
                col_map, col_chart = st.columns(2)

                with col_map:
                    st.markdown("**Locations of Ecostations and Garage**")
                    map_data = prepared_data['ecostation_data'].head(num_existing_stations)[['Latitude', 'Longitude']].copy()
                    garage_df = pd.DataFrame([{'Latitude': prepared_data['garage_location']['Latitude'], 'Longitude': prepared_data['garage_location']['Longitude']}])
                    final_map_df = pd.concat([map_data, garage_df], ignore_index=True)
                    
                    # **FIX**: Rename columns to the lowercase format required by st.map
                    final_map_df.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'}, inplace=True)
                    
                    st.map(final_map_df, zoom=10)

                with col_chart:
                    st.markdown("**Trips per Ecostation**")
                    trips_by_station = prepared_data['ecostation_data'].head(num_existing_stations).copy()
                    avg_collection_size = trips_by_station['Max Capacity (kg)'] * params['CAPACITY_TRIGGER_PERCENT']
                    trips_by_station['Estimated Trips'] = (trips_by_station['Accumulation Rate (kg/day)'] * params['SIMULATION_DAYS']) / avg_collection_size
                    st.bar_chart(trips_by_station.set_index('Service Point')['Estimated Trips'])


            with data_tab:
                st.header("Backend Data & Calculations")
                st.write("This section shows the data calculated in the background, which feeds the simulation.")
                
                st.subheader("Calculated Ecostation Metrics")
                st.dataframe(prepared_data['ecostation_data'].head(num_existing_stations).round(2))
                
                st.subheader("Direct Trip Durations (Hours)")
                st.dataframe(pd.DataFrame.from_dict(prepared_data['trip_times'], orient='index', columns=['Total Trip Hours']).round(2))
                
                st.subheader("Distance Matrix (km)")
                st.dataframe(prepared_data['distance_matrix_km'].iloc[:num_existing_stations+1, :num_existing_stations+1])


        except Exception as e:
            st.error(f"An error occurred during analysis: {e}")
            st.exception(e)

else:
    st.info("Adjust the parameters in the sidebar and click 'Run Analysis' to start the simulation.")
