import time
from cassandra.cluster import Cluster
from api.config import settings

_cassandra_session = None

def init_cassandra_db():
    global _cassandra_session
    
    retries = 30
    while retries > 0:
        cluster = None
        
        try:
            cluster = Cluster([settings.CASSANDRA_HOST], port=settings.CASSANDRA_PORT, connect_timeout=15)
            session = cluster.connect()
            
            session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
                WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}};
            """)
            
            session.execute(f"USE {settings.CASSANDRA_KEYSPACE};")
            
            session.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    sensor_id text,
                    reading_time timestamp,
                    metric_type text,
                    value float,
                    unit text,
                    quality_flag tinyint,
                    PRIMARY KEY ((sensor_id), reading_time)
                ) WITH CLUSTERING ORDER BY (reading_time DESC)
                  AND default_time_to_live = 7776000;
            """)
            
            session.execute("""
                CREATE TABLE IF NOT EXISTS relay_events (
                    feeder_id text,
                    event_time timeuuid,
                    relay_id text,
                    event_type text,
                    fault_type text,
                    current_kA float,
                    PRIMARY KEY ((feeder_id), event_time)
                ) WITH CLUSTERING ORDER BY (event_time ASC);
            """)
            
            _cassandra_session = session
            print("Successfully initialized Cassandra with official assignment schema!")
            return
            
        except Exception as e:
            print(f"Cassandra is not ready yet, retrying... ({retries} left). Error: {e}")
            if cluster:
                try:
                    cluster.shutdown()
                except:
                    pass
            time.sleep(3)
            retries -= 1
            
    raise Exception("Could not connect to Cassandra after multiple attempts.")

def get_cassandra_session():
    global _cassandra_session
    return _cassandra_session