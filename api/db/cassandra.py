import time
from cassandra.cluster import Cluster
from api.config import settings

_cassandra_session = None

def init_cassandra_db():
    global _cassandra_session
    
    retries = 20

    while retries > 0:
        cluster = None
        try:

            cluster = Cluster([settings.CASSANDRA_HOST], port=settings.CASSANDRA_PORT, connect_timeout=10)
            session = cluster.connect()
            
            session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
                WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
            """)
            
            session.set_keyspace(settings.CASSANDRA_KEYSPACE)
            
            session.execute("""
                CREATE TABLE IF NOT EXISTS meter_readings (
                    meter_id text,
                    timestamp timestamp,
                    energy_kwh double,
                    voltage double,
                    frequency double,
                    PRIMARY KEY (meter_id, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC);
            """)
            
            _cassandra_session = session

            print(f"Cassandra Database & 'meter_readings' table initialized successfully.")
            return
            
        except Exception as e:

            print(f"Cassandra is not ready yet, retrying... ({retries} left). Error: {e}")

            if cluster:
                try:
                    cluster.shutdown()
                except:
                    pass
            time.sleep(5)
            retries -= 1
            
    raise Exception("Could not connect to Cassandra after multiple attempts.")

def get_cassandra_session():
    global _cassandra_session
    return _cassandra_session