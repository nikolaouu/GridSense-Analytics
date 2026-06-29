CREATE KEYSPACE IF NOT EXISTS gridsense 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE gridsense;

-- Πίνακας 1: Time-Series Μετρήσεων Αισθητήρων με TTL 90 ημερών (Section B.3)
CREATE TABLE IF NOT EXISTS sensor_readings (
    sensor_id text,
    reading_time timestamp,
    metric_type text,
    value double,
    unit text,
    quality_flag text,
    PRIMARY KEY ((sensor_id), metric_type, reading_time)
) WITH CLUSTERING ORDER BY (metric_type ASC, reading_time DESC)
  AND default_time_to_live = 7776000;

-- Πίνακας 2: Συμβάντα Αναμεταδοτών (Section B.3) με TIMEUUID για διατήρηση της αιτιατής σειράς
CREATE TABLE IF NOT EXISTS relay_events (
    relay_id text,
    event_time timeuuid,
    event_type text,
    status text,
    details text,
    PRIMARY KEY ((relay_id), event_time)
) WITH CLUSTERING ORDER BY (event_time DESC);

-- Πίνακας Query Pattern (2): Live Dashboard για αποφυγή ALLOW FILTERING
-- Οργανώνει τις μετρήσεις ανά λεπτό (π.χ. "202606291401") ως Partition Key.
-- Έτσι, για τα τελευταία 60 δευτερόλεπτα διαβάζουμε στοχευμένα μόνο 1 ή 2 partitions.
CREATE TABLE IF NOT EXISTS active_dashboard_readings (
    minute_bucket text, 
    reading_time timestamp,
    sensor_id text,
    metric_type text,
    value double,
    PRIMARY KEY ((minute_bucket), reading_time, sensor_id)
) WITH CLUSTERING ORDER BY (reading_time DESC, sensor_id ASC)
  AND default_time_to_live = 300; -- Αυτόματη διαγραφή μετά από 5 λεπτά