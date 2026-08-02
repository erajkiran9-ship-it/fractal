import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import (
    collector,
    communications,
    customers,
    disputes,
    invoices,
    notifications,
    payments,
    simulation,
    workflows,
)

app = FastAPI(
    title="CPG Collections Workflow Agent",
    description="AI-powered collections workflow engine for Consumer Packaged Goods",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(customers.router)
app.include_router(invoices.router)
app.include_router(workflows.router)
app.include_router(communications.router)
app.include_router(payments.router)
app.include_router(disputes.router)
app.include_router(collector.router)
app.include_router(simulation.router)
app.include_router(notifications.router)


@app.get("/")
def root():
    return {
        "name": "CPG Collections Workflow Agent",
        "version": "1.0.0",
        "status": "running",
        "portals": {
            "manager": "http://localhost:3000/manager",
            "customer": "http://localhost:3000/customer/{customer_id}",
            "collector": "http://localhost:3000/collector",
        }
    }


@app.get("/api/health")
def health():
    from backend.data_layer import excel_store as db
    from backend.agent.azure_openai import missing_configuration
    from backend.config import AZURE_OPENAI_DEPLOYMENT

    state = db.get_system_state()
    missing = missing_configuration()
    return {
        "status": "healthy",
        "current_date": state.get("current_date"),
        "cycle_count": state.get("cycle_count", 0),
        "model_provider": "azure_openai",
        "model_deployment": AZURE_OPENAI_DEPLOYMENT,
        "model_configured": not missing,
        "missing_model_configuration": missing,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
