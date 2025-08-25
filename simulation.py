# simulation.py

def run_simulation(num_stations_to_sim, num_trucks, station_data, trip_data, params):
    """Operasyonel simülasyonu çalıştıran ana fonksiyon."""
    sim_stations = station_data.head(num_stations_to_sim).copy()
    sim_stations['current_waste_kg'] = 0.0
    
    trucks = [{'id': i, 'busy_until_hour': 0.0, 'total_work_hours': 0.0} for i in range(num_trucks)]
    
    collection_queue = []
    service_failures = {name: 0 for name in sim_stations['Service Point']}
    total_trips = 0
    simulation_duration_hours = int(params['SIMULATION_DAYS'] * 24)

    for hour in range(simulation_duration_hours):
        current_day = hour // 24
        
        if hour > 0 and hour % 24 == 0:
            for truck in trucks:
                truck['busy_until_hour'] = max(truck['busy_until_hour'], float(hour))

        sim_stations['current_waste_kg'] += sim_stations['accumulation_rate_kg_day'] / 24.0
        
        trigger_level = sim_stations['max_capacity_kg'] * params['CAPACITY_TRIGGER_PERCENT']
        triggered_stations = sim_stations[sim_stations['current_waste_kg'] >= trigger_level]
        
        for idx, station_row in triggered_stations.iterrows():
            station_name = station_row['Service Point']
            if station_name not in [item['name'] for item in collection_queue]:
                 collection_queue.append({'name': station_name, 'triggered_at_hour': hour})
        
        if collection_queue:
            collection_queue.sort(key=lambda x: x['triggered_at_hour'])
            
            requests_to_keep = list(collection_queue)
            for request in collection_queue:
                station_name = request['name']
                trip_duration = trip_data[station_name]
                
                truck_found_for_request = False
                for truck in sorted(trucks, key=lambda t: t['busy_until_hour']):
                    start_of_shift = (hour // 24) * 24
                    end_of_shift = start_of_shift + params['DAILY_WORK_HOURS']
                    potential_start_time = max(float(hour), truck['busy_until_hour'])
                    
                    if (potential_start_time + trip_duration) <= end_of_shift:
                        truck['busy_until_hour'] = potential_start_time + trip_duration
                        truck['total_work_hours'] += trip_duration
                        sim_stations.loc[sim_stations['Service Point'] == station_name, 'current_waste_kg'] = 0.0
                        total_trips += 1
                        truck_found_for_request = True
                        requests_to_keep.remove(request)
                        break
                
                if not truck_found_for_request:
                    if (hour - request['triggered_at_hour']) > 24:
                        service_failures[station_name] += 1
                        sim_stations.loc[sim_stations['Service Point'] == station_name, 'current_waste_kg'] = 0.0
                        if request in requests_to_keep:
                            requests_to_keep.remove(request)

            collection_queue = requests_to_keep
            
    total_hours_worked = sum(t['total_work_hours'] for t in trucks)
    total_hours_available = num_trucks * params['DAILY_WORK_HOURS'] * params['SIMULATION_DAYS']
    utilization = (total_hours_worked / total_hours_available) * 100 if total_hours_available > 0 else 0
    
    return {
        "utilization_percent": utilization,
        "total_trips": total_trips,
        "service_failures": sum(service_failures.values()),
        "failures_by_station": service_failures
    }
