import requests
import random
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

requests.post(f"{BASE_URL}/topology/nodes", json={"asset_id": "SUB-CENTRAL", "asset_type": "Substation", "location": "Athens Center"})

transformers = ["TRF-ALPHA", "TRF-BETA"]

for trf in transformers:

    requests.post(f"{BASE_URL}/topology/nodes", json={"asset_id": trf, "asset_type": "Transformer", "location": "Attica Region"})
    requests.post(f"{BASE_URL}/topology/relationships", json={"source_id": "SUB-CENTRAL", "target_id": trf})

meters = []

for i in range(1, 6):

    meter_id = f"MTR-10{i}"
    meters.append(meter_id)
    requests.post(f"{BASE_URL}/topology/nodes", json={"asset_id": meter_id, "asset_type": "SmartMeter", "location": f"Household-{i}"})
    
    parent_trf = "TRF-ALPHA" if i <= 3 else "TRF-BETA"
    requests.post(f"{BASE_URL}/topology/relationships", json={"source_id": parent_trf, "target_id": meter_id})

now = datetime.utcnow()
for meter_id in meters:
    
    base_energy = 100.0
    
    for hour in range(10, 0, -1):

        timestamp = (now - timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M:%SZ")
        base_energy += random.uniform(1.2, 3.5)
        voltage = random.uniform(228.0, 232.0)
        frequency = random.uniform(49.95, 50.05)
        
        payload = {
            "meter_id": meter_id,
            "timestamp": timestamp,
            "energy_kwh": round(base_energy, 2),
            "voltage": round(voltage, 1),
            "frequency": round(frequency, 2)
        }
        
        requests.post(f"{BASE_URL}/measurements", json=payload)

start_time = time.time()
res1 = requests.get(f"{BASE_URL}/topology/trace-downstream/TRF-ALPHA").json()

print(f"Found {res1['affected_meters_count']} affected meters in {round((time.time() - start_time) * 1000, 2)} ms")

start_time = time.time()
res2 = requests.get(f"{BASE_URL}/topology/trace-downstream/TRF-ALPHA").json()
print(f"Found {res2['affected_meters_count']} affected meters in {round((time.time() - start_time) * 1000, 2)} ms")
