from fastapi import APIRouter
from backend.data_layer import excel_store as db
from backend.workflow_plan import WorkflowPlanError, parse_workflow_plan

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _with_parsed_plan(workflow: dict) -> dict:
    try:
        workflow["plan"] = parse_workflow_plan(workflow.get("plan_json", {}))
    except WorkflowPlanError:
        workflow["plan"] = {}
    return workflow


@router.get("")
def get_all_workflows():
    workflows = db.get_all_workflows()
    workflows = [_with_parsed_plan(wf) for wf in workflows]
    return {"workflows": workflows}


@router.get("/active")
def get_active_workflows():
    workflows = db.get_active_workflows()
    workflows = [_with_parsed_plan(wf) for wf in workflows]
    return {"workflows": workflows}


@router.get("/invoice/{invoice_id}")
def get_workflow_by_invoice(invoice_id: str):
    workflow = db.get_workflow_by_invoice(invoice_id)
    if not workflow:
        return {"workflow": None}
    return {"workflow": _with_parsed_plan(workflow)}
