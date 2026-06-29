# GridSense API - Smart Power Grid Analytics Platform

This repository contains the official implementation of **GridSense**, a multi-database (Polyglot Persistence) smart power grid analytics platform designed for the *Advanced Data Management* final assignment at the University of Thessaly (ECE Department).

The platform uses **FastAPI** to orchestrate and handle multi-rate ingestion, graph topology traversals, time-series telemetry, and relational billing across 5 distinct database engines.

---

## 1. System Architecture & Technologies

GridSense partitions its data domain based on operational requirements to prevent bottlenecks:
- **FastAPI**: Main application framework and routing engine.
- **PostgreSQL (`billing-db`)**: Handles structured billing schemas, accounts, and financial transactions with full ACID guarantees, utilizing `JSONB` for dynamic consumer metadata.
- **MongoDB (`catalog-db`)**: Acts as the equipment catalog, storing highly heterogeneous physical asset specifications from multiple manufacturers.
- **Neo4j (`graph-db`)**: Manages the grid topology network, mapping substations, transformers, and lines to perform sub-second electrical fault-impact and path restoration queries.
- **Cassandra (`timeseries-db`)**: Ingests massive volumes of high-rate telemetry, smart meter readings, and sub-station logs utilizing time-series wide-column storage.
- **Redis (`cache`)**: Serves as an ultra-fast in-memory stroke-buffer cache for real-time telemetry updates and coordinates reactive system alerts via Pub/Sub.

---

## 2. Prerequisites

Ensure you have the following installed on your system:
- **Docker** (v20.10 or higher)
- **Docker Compose** (v2.0 or higher)

---

## 3. Installation & Setup

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd gridsense
