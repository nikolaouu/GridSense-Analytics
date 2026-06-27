from cassandra.cluster import Cluster
import os
import time

_cassandra_session = None

def init_cassandra_db():
    global _cassandra_session
    cassandra_host = os.getenv("CASSANDRA_HOST", "cassandra")
    
    retries = 15
    while retries > 0:
        try:
            print(f"Connecting to Cassandra at {cassandra_host}... ({retries} retries left)")
            cluster = Cluster([cassandra_host])
            session = cluster.connect()
            
            session.execute("""
                CREATE KEYSPACE IF NOT EXISTS gridsense_ts
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
            """)
            
            session.set_keyspace('gridsense_ts')
            
            session.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    asset_id text,
                    timestamp timestamp,
                    power_kw double,
                    voltage_v double,
                    current_a double,
                    PRIMARY KEY (asset_id, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC);
            """)
            
            _cassandra_session = session
            print("Cassandra session initialized and schema created successfully.")
            return
        except Exception as e:
            print(f"Cassandra is bootstrapping or not ready yet. Retrying in 5s... Error: {e}")
            time.sleep(5)
            retries -= 1
            
    raise Exception("Could not connect to Cassandra after multiple attempts.")

def get_cassandra_session():
    global _cassandra_session
    return _cassandra_session