from sqlalchemy.orm import Session

from app.services.rag import search_knowledge_base
from app.services.tool_functions import (
    check_outage,
    create_ticket,
    get_account_status,
    get_ticket_status,
    run_remote_diagnostics,
    schedule_technician_visit,
    get_payment_history,
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_outage",
            "description": "Check if there is an internet outage in a specific city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the knowledge base for technical guides, setup, and billing plans.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
       {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a standalone support ticket. Use this ONLY for non-physical issues that need tracking but do NOT require a technician visit (e.g., billing disputes, general inquiries). Do NOT use this if a technician needs to visit the client.",
            "parameters": {"type": "object", "properties": {"issue_summary": {"type": "string"}}, "required": ["issue_summary"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_technician_visit",
            "description": "Schedule a physical technician visit. IMPORTANT: This tool AUTOMATICALLY creates the associated support ticket for you. Do NOT call create_ticket if you use this. You MUST ask the user for their preferred date and time slot BEFORE calling this tool. Only call this if remote troubleshooting (KB search, diagnostics) failed or confirmed a physical hardware/line issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string"},
                    "preferred_date": {"type": "string"},
                    "time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"]},
                },
                "required": ["issue_type", "preferred_date", "time_slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_status",
            "description": "Look up the user's specific account details, current internet plan, and billing balance.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket_status",
            "description": "Check the current status of a support ticket.",
            "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_remote_diagnostics",
            "description": "Run a remote signal test on the fiber line connecting to the user's home.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
        {
        "type": "function",
        "function": {
            "name": "get_payment_history",
            "description": "Look up the user's recent payment transactions to check if a payment went through or view past billing activity.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


async def execute_tool(
    db: Session,
    session_id: str,
    user_id: str,
    tool_name: str,
    arguments: dict,
    transcript_str: str,
) -> str:
    dispatch = {
        "check_outage": lambda: check_outage(db=db, city=arguments.get("city", "")),
        "create_ticket": lambda: create_ticket(
            db=db, session_id=session_id, user_id=user_id,
            issue_summary=arguments.get("issue_summary", "No summary provided"), transcript=transcript_str,
        ),
        "schedule_technician_visit": lambda: schedule_technician_visit(
            db=db, session_id=session_id, user_id=user_id,
            issue_type=arguments.get("issue_type", "Unknown issue"),
            preferred_date=arguments.get("preferred_date", "tomorrow"),
            time_slot=arguments.get("time_slot", "morning"), transcript=transcript_str,
        ),
        "search_knowledge_base": lambda: search_knowledge_base(
            query=arguments.get("query", ""), db=db, user_id=user_id, session_id=session_id,
        ),
        "get_account_status": lambda: get_account_status(db=db, user_id=user_id),
        "get_ticket_status": lambda: get_ticket_status(db=db, ticket_id=arguments.get("ticket_id", "")),
        "run_remote_diagnostics": lambda: run_remote_diagnostics(session_id=session_id),
        "get_payment_history": lambda: get_payment_history(db=db, user_id=user_id), 
    }

    handler = dispatch.get(tool_name)
    if not handler:
        return "Tool not found."

    try:
        result = handler()
        if hasattr(result, "__await__"):
            return await result
        return result
    except Exception as e:
        print(f"EXECUTE_TOOL CRASHED: {e}")
        return "There was an error executing the tool."