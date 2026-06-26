from fastapi import FastAPI

app = FastAPI(
    title="GridSense API",
    description="Advanced Data Management - Smart Power Grid Analytics Platform",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to GridSense Smart Grid Analytics Platform API"
    }

@app.get("/health")
def health_check():
    # Εδώ αργότερα θα ελέγχουμε αν οι βάσεις είναι ζωντανές
    return {"status": "healthy"}