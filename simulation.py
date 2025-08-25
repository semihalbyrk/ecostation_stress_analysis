# simulation.py

def run_simulation(station_data, trip_times, params):
    """
    Runs the operational simulation based on the provided data and parameters.
    This version uses the updated logic for an 8-hour workday and overflow-based service failures.
    """
    # --- 1. INITIALIZATION ---
    sim_stations = station_data.copy()
    sim_stations['current_waste_kg'] = 0.0
    
    num_trucks = params['NUM_TRUCKS']
    trucks = [{'id': i, 'busy_until_hour': 0.0, 'total_work_hours': 0.0} for i in range(num_trucks)]
    
    collection_queue = []
    service_failures = {name: 0 for name in sim_stations['Service Point']}
    total_trips = 0
    simulation_duration_hours = int(params['SIMULATION_DAYS'] * 24)
    
    # Define working hours for the simulation day (e.g., 08:00 to 16:00)
    WORK_DAY_START_HOUR = 8
    WORK_DAY_END_HOUR = WORK_DAY_START_HOUR + params['ECOSTATION_WORK_HOURS']

    # --- 2. TIME-BASED SIMULATION LOOP ---
    for hour in range(simulation_duration_hours):
        current_day = hour // 24
        hour_of_day = hour % 24
        
        # --- Waste Accumulation (NEW LOGIC) ---
        # Waste only accumulates during the defined working hours
        if WORK_DAY_START_HOUR <= hour_of_day < WORK_DAY_END_HOUR:
            hourly_rate = sim_stations['Accumulation Rate (kg/day)'] / params['ECOSTATION_WORK_HOURS']
            sim_stations['current_waste_kg'] += hourly_rate

        # --- Service Failure Check (NEW LOGIC) ---
        # Check for overflows BEFORE dispatching. A failure happens the moment capacity is breached.
        overflowed_stations_mask = sim_stations['current_waste_kg'] > sim_stations['Max Capacity (kg)']
        overflowed_station_names = sim_stations[overflowed_stations_mask]['Service Point'].tolist()

        if overflowed_station_names:
            for station_name in overflowed_station_names:
                 # Check if this station is already in the queue (i.e., its collection is pending)
                is_in_queue = any(req['name'] == station_name for req in collection_queue)
                if is_in_queue:
                    service_failures[station_name] += 1
                    # Reset waste to prevent multiple failure counts for the same event
                    sim_stations.loc[sim_stations['Service Point'] == station_name, 'current_waste_kg'] = 0.0
                    # Remove from queue as it has failed and is now considered "serviced" (albeit late)
                    collection_queue = [req for req in collection_queue if req['name'] != station_name]


        # --- Trigger Collection Requests ---
        trigger_level = sim_stations['Max Capacity (kg)'] * params['CAPACITY_TRIGGER_PERCENT']
        triggered_stations_mask = sim_stations['current_waste_kg'] >= trigger_level
        
        for idx, station_row in sim_stations[triggered_stations_mask].iterrows():
            station_name = station_row['Service Point']
            if not any(req['name'] == station_name for req in collection_queue):
                 collection_queue.append({'name': station_name, 'triggered_at_hour': hour})
        
        # --- Dispatch Trucks ---
        if collection_queue:
            collection_queue.sort(key=lambda x: x['triggered_at_hour']) # Prioritize oldest request
            
            requests_to_keep = list(collection_queue)
            for request in collection_queue:
                station_name = request['name']
                trip_duration = trip_times[station_name]
                
                truck_found = False
                for truck in sorted(trucks, key=lambda t: t['busy_until_hour']):
                    shift_start_hour = (hour // 24) * 24 + WORK_DAY_START_HOUR
                    shift_end_hour = shift_start_hour + params['DAILY_WORK_HOURS']
                    
                    potential_start_time = max(float(hour), truck['busy_until_hour'], shift_start_hour)
                    
                    if (potential_start_time + trip_duration) <= shift_end_hour:
                        truck['busy_until_hour'] = potential_start_time + trip_duration
                        truck['total_work_hours'] += trip_duration
                        sim_stations.loc[sim_stations['Service Point'] == station_name, 'current_waste_kg'] = 0.0
                        total_trips += 1
                        truck_found = True
                        requests_to_keep.remove(request)
                        break
            
            collection_queue = requests_to_keep
            
    # --- 3. CALCULATE FINAL METRICS ---
    total_hours_worked = sum(t['total_work_hours'] for t in trucks)
    total_hours_available = num_trucks * params['DAILY_WORK_HOURS'] * params['SIMULATION_DAYS']
    utilization = (total_hours_worked / total_hours_available) * 100 if total_hours_available > 0 else 0
    
    return {
        "utilization_percent": utilization,
        "total_trips": total_trips,
        "service_failures": sum(service_failures.values()),
        "failures_by_station": service_failures,
        "total_hours_worked": total_hours_worked,
        "total_hours_available": total_hours_available,
    }
