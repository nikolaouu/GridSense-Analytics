from cassandra.cluster import Cluster
import asyncio
from api.config import settings

_cassandra_session = None

async def init_cassandra_db():
    global _cassandra_session
    retries = 10
    
    while retries > 0:
        try:

            cluster = Cluster([settings.CASSANDRA_HOST], port=settings.CASSANDRA_PORT)
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
                    voltage double,
                    current_load double,
                    frequency double,
                    status_code int,
                    PRIMARY KEY (meter_id, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC);
            """)
            
            _cassandra_session = session
            print("Cassandra Time-Series Database initialized successfully.")
            return
        except Exception as e:
            print(f"Cassandra not ready, retrying... ({retries} left). Error: {e}")
            await asyncio.sleep(4)
            retries -= 1
            
    raise Exception("Could not connect to Cassandra")

def get_cassandra_session():
    global _cassandra_session
    return _cassandra_session