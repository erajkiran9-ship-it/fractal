from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import subprocess
import sys
from pathlib import Path
from backend.data_layer import excel_store as db
from backend.agent.runner import run_daily_cycle
from backend.agent.azure_openai import missing_configuration
from backend.date_utils import parse_date

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.get("/state")
def get_system_state():
    """Get current system state including date and cycle count."""
    state = db.get_system_state()
    return state


def _advance_simulation(days: int):
    """Move the simulation clock and run one agent cycle on the target date."""
    state = db.get_system_state()
    current_date_str = state.get("current_date", "2026-08-01")
    missing = missing_configuration()
    if missing:
        message = f"Missing Azure OpenAI configuration: {', '.join(missing)}"
        return {
            "status": "error",
            "new_date": current_date_str,
            "days_advanced": 0,
            "error": message,
            "agent_result": {
                "date": current_date_str,
                "cycle_number": state.get("cycle_count", 0),
                "iterations": 0,
                "tool_calls": 0,
                "tool_calls_log": [],
                "agent_reasoning": f"API Error: {message}",
                "status": "error",
                "provider": "azure_openai",
            },
        }
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
    new_date = current_date + timedelta(days=days)
    new_date_str = new_date.strftime("%Y-%m-%d")

    # Update system date
    state["current_date"] = new_date_str
    db.save_system_state(state)

    # Run the agent's daily cycle
    try:
        result = run_daily_cycle(new_date_str)
        if result.get("status") == "error":
            state["current_date"] = current_date_str
            db.save_system_state(state)
            return {
                "status": "error",
                "new_date": current_date_str,
                "attempted_date": new_date_str,
                "days_advanced": 0,
                "error": result.get("agent_reasoning", "Agent cycle failed"),
                "agent_result": result,
            }
        return {
            "status": "success",
            "new_date": new_date_str,
            "days_advanced": days,
            "agent_result": result,
        }
    except Exception as e:
        state["current_date"] = current_date_str
        db.save_system_state(state)
        return {
            "status": "error",
            "new_date": current_date_str,
            "attempted_date": new_date_str,
            "days_advanced": 0,
            "error": str(e),
        }


@router.post("/advance-day")
def advance_day():
    """Advance one day and run the agent's daily cycle."""
    return _advance_simulation(1)


@router.post("/advance-three-days")
def advance_three_days():
    """Jump three days and run one agent cycle on the resulting date."""
    return _advance_simulation(3)


@router.post("/reset")
def reset_system():
    """Reset the system to initial state by regenerating all data."""
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    generate_script = scripts_dir / "generate_data.py"

    try:
        subprocess.run(
            [sys.executable, str(generate_script)],
            check=True,
            capture_output=True,
            text=True
        )
        return {"status": "reset", "message": "System reset to August 1, 2026"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": str(e.stderr)}


@router.get("/aging-summary")
def get_aging_summary():
    """Get aging bucket summary across all customers."""
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")
    today = parse_date(current_date)

    invoices = db.get_open_invoices()
    buckets = {"current": 0, "1-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    for inv in invoices:
        due = parse_date(inv["due_date"])
        days = (today - due).days
        amount = float(inv.get("amount", 0)) - float(inv.get("amount_paid", 0) or 0)
        if days <= 0:
            buckets["current"] += amount
        elif days <= 30:
            buckets["1-30"] += amount
        elif days <= 60:
            buckets["31-60"] += amount
        elif days <= 90:
            buckets["61-90"] += amount
        else:
            buckets["90+"] += amount

    return {"aging": buckets, "total": sum(buckets.values()), "current_date": current_date}


@router.get("/credit-exposure")
def get_credit_summary():
    """Get credit exposure for all customers."""
    credit = db.get_all_credit_exposure()
    return {"credit_exposure": credit}
