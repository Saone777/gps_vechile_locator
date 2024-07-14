import simpy
import random
from geopy.distance import geodesic
from shapely.geometry import Point, Polygon
import folium
import pandas as pd
from datetime import datetime

# Constants
TOLL_RATE_PER_KM = 0.05 * 82  # Assuming 1 USD = 82 INR
FIXED_TOLL_FEE = 2.00 * 82  # Assuming 1 USD = 82 INR
DYNAMIC_PRICING_RATE = 0.02 * 82  # Assuming 1 USD = 82 INR
CONGESTION_THRESHOLD = 10
TIME_SLOT_RATE = {
    'peak': 0.03 * 82,  # Assuming 1 USD = 82 INR
    'off_peak': 0.01 * 82  # Assuming 1 USD = 82 INR
}
SPEED_LIMIT_SECTIONS = {
    'section_1': 60,
    'section_2': 80,
    'section_3': 100
}
TOLL_ROAD_LENGTH = 100  # km

# Payment vendors
VENDORS = ['Vendor_A', 'Vendor_B', 'Vendor_C']

# Randomly generate toll zones
def generate_toll_zones(n_zones):
    zones = []
    for _ in range(n_zones):
        lat = random.uniform(13.0, 13.9)
        lon = random.uniform(80.0, 80.9)
        radius = random.uniform(0.1, 0.2)  # Approximate radius for the zone
        zones.append(Point(lat, lon).buffer(radius))
    return zones

# Generate random route
def generate_route():
    return [(random.uniform(13.0, 13.9), random.uniform(80.0, 80.9)) for _ in range(random.randint(5, 15))]

# Determine time slot for dynamic pricing
def get_time_slot():
    current_hour = datetime.now().hour
    if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
        return 'peak'
    else:
        return 'off_peak'

# Vehicle class
class Vehicle:
    def __init__(self, env, vehicle_id, start, end, account, toll_zones, route):
        self.env = env
        self.vehicle_id = vehicle_id
        self.start = start
        self.end = end
        self.position = start
        self.account = account
        self.toll_zones = toll_zones
        self.route = route
        self.process = env.process(self.run())
        self.stationary_time = 0

    def run(self):
        for position in self.route:
            if self.stationary_time >= 5:
                print(f'Emergency contingency: {self.vehicle_id} has been stationary for 5 time units.')
                break

            self.position = position
            self.check_toll_zone()
            self.check_speed_limit()
            yield self.env.timeout(1)
            if random.random() < 0.1:  # Randomly generate congestion
                yield self.env.timeout(1)

            # Check if vehicle is stationary
            if self.position == self.route[-1]:
                self.stationary_time += 1
            else:
                self.stationary_time = 0

    def check_toll_zone(self):
        for toll_zone in self.toll_zones:
            if toll_zone.contains(Point(self.position)):
                distance = calculate_distance(self.start, self.position)
                toll = calculate_toll(distance)
                self.account.deduct_toll(toll)
                print(f'{self.vehicle_id} crossed toll zone. Toll: {toll:.2f} INR, Remaining balance: {self.account.balance:.2f} INR')

    def check_speed_limit(self):
        for section, limit in SPEED_LIMIT_SECTIONS.items():
            if calculate_distance(self.start, self.position) > limit:
                print(f'{self.vehicle_id} exceeded speed limit in {section}. Speed limit: {limit} km/h')

# UserAccount class
class UserAccount:
    def __init__(self, balance, vendor):
        self.balance = balance
        self.vendor = vendor
        self.payments = []

    def deduct_toll(self, amount):
        self.balance -= amount
        self.payments.append(amount)
        return self.balance

# Calculate distance between two points
def calculate_distance(start, end):
    return geodesic(start, end).kilometers

# Calculate toll based on distance and dynamic pricing
def calculate_toll(distance):
    toll = distance * TOLL_RATE_PER_KM + FIXED_TOLL_FEE
    time_slot = get_time_slot()
    toll += distance * TIME_SLOT_RATE[time_slot]
    if distance > CONGESTION_THRESHOLD:
        toll += distance * DYNAMIC_PRICING_RATE
    return toll

# Setup the simulation environment
def setup_environment(env, vehicles):
    for vehicle in vehicles:
        env.process(vehicle.run())

# Visualize vehicle movements and toll zones on a map
def visualize_movements(vehicles, toll_zones):
    m = folium.Map(location=[13.0827, 80.2707], zoom_start=12)  # Center map on Chennai
    
    for vehicle in vehicles:
        folium.Marker(location=vehicle.position, popup=vehicle.vehicle_id).add_to(m)
    
    for toll_zone in toll_zones:
        folium.GeoJson(toll_zone).add_to(m)
    
    return m

# Generate analytics report
def generate_report(vehicles):
    report = {
        "Vehicle ID": [],
        "Total Distance Traveled (km)": [],
        "Total Toll Paid (INR)": [],
        "Payment Vendor": []
    }
    for vehicle in vehicles:
        total_distance = calculate_distance(vehicle.start, vehicle.end)
        total_toll = sum(vehicle.account.payments)
        report["Vehicle ID"].append(vehicle.vehicle_id)
        report["Total Distance Traveled (km)"].append(total_distance)
        report["Total Toll Paid (INR)"].append(total_toll)
        report["Payment Vendor"].append(vehicle.account.vendor)
    
    df = pd.DataFrame(report)
    df.to_csv("toll_report_new.csv", index=False)
    print("Report generated: toll_report_new.csv")

# Query the number of vehicles on the toll road
def query_vehicle_count(env, vehicles):
    return sum(1 for vehicle in vehicles if vehicle.env.now <= env.now)

# Define the main function
def main():
    env = simpy.Environment()
    toll_zones = generate_toll_zones(5)
    vehicles = []
    
    for i in range(10):  # Create 10 vehicles
        route = generate_route()
        account = UserAccount(100, random.choice(VENDORS))
        vehicle = Vehicle(env, f'Vehicle_{i}', route[0], route[-1], account, toll_zones, route)
        vehicles.append(vehicle)
    
    setup_environment(env, vehicles)
    env.run(until=100)

    m = visualize_movements(vehicles, toll_zones)
    m.save("vehicle_movements_area.html")
    
    generate_report(vehicles)

    print(f'Number of vehicles on the toll road: {query_vehicle_count(env, vehicles)}')

if __name__ == "__main__":
    main()
