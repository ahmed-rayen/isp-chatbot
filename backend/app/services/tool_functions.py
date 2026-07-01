import random
import uuid
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import Outage, Technician, TechnicianVisit, Ticket, User, Payment


def check_outage(db: Session, city: str) -> str:
    city_formatted = city.lower().strip()
    outage = (
        db.query(Outage)
        .filter(func.lower(Outage.city) == city_formatted, Outage.is_deleted == False)  # noqa: E712
        .first()
    )
    if outage:
        if outage.is_active:
            return f"There is an active issue in {city.title()}: {outage.status}"
        return f"All systems are operational in {city.title()}."
    return f"No outage information available for {city.title()}."


def get_account_status(db: Session, user_id: str) -> str:
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        return "User account not found."
    return f"Account Found: {user.name}. Current Plan: {user.plan}. Balance Due: {user.balance} TND by {user.due_date}."


def get_ticket_status(db: Session, ticket_id: str) -> str:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        return f"Ticket {ticket_id} not found."
    return f"Ticket {ticket.id} status: {ticket.status}. Issue: {ticket.issue_summary}."


def run_remote_diagnostics(session_id: str) -> str:
    signal_dbm = random.randint(-25, -15)
    if signal_dbm > -20:
        return f"Diagnostic complete. Fiber signal is excellent ({signal_dbm} dBm). The physical line to the home is intact."
    return f"Diagnostic complete. Fiber signal is weak ({signal_dbm} dBm). Recommend dispatching a technician."


def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str, transcript: str = "") -> str:
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id,
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(user_id),
        issue_summary=issue_summary,
        transcript=transcript,
        status="open",
    )
    db.add(new_ticket)
    db.commit()

    from app.services.notifications import send_notification
    send_notification(db, user_id, f"Your support ticket {ticket_id} has been created.")
    return f"Ticket {ticket_id} created successfully."


def schedule_technician_visit(
    db: Session,
    session_id: str,
    user_id: str,
    issue_type: str,
    preferred_date: str,
    time_slot: str,
    transcript: str = "",
) -> str:
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id,
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(user_id),
        issue_summary=f"Technician Visit Required: {issue_type}",
        transcript=transcript,
        status="visit_scheduled",
    )
    db.add(new_ticket)
    db.flush()

    # Parse preferred date
    try:
        lower_date = preferred_date.lower()
        if "after" in lower_date:
            days_add = 2
        elif "tomorrow" in lower_date or "demain" in lower_date:
            days_add = 1
        else:
            visit_date = date.fromisoformat(preferred_date)
            days_add = None
        if days_add is not None:
            visit_date = date.today() + timedelta(days=days_add)
    except Exception:
        visit_date = date.today() + timedelta(days=1)

    # Find least loaded technician for the date
    tech_counts = (
        db.query(TechnicianVisit.technician_id, func.count(TechnicianVisit.id))
        .filter(TechnicianVisit.scheduled_date == visit_date)
        .group_by(TechnicianVisit.technician_id)
        .all()
    )
    all_techs = db.query(Technician).all()
    chosen_tech = None

    for tech_id, count in tech_counts:
        for t in all_techs:
            if t.id == tech_id and count < t.daily_capacity:
                chosen_tech = t
                break
        if chosen_tech:
            break

    # If no techs have visits that day, pick any available
    if not chosen_tech and all_techs:
        chosen_tech = all_techs[0]

    if not chosen_tech:
        db.rollback()
        return "Sorry, all technicians are fully booked for that date."

    new_visit = TechnicianVisit(
        ticket_id=ticket_id,
        user_id=uuid.UUID(user_id),
        technician_id=chosen_tech.id,
        scheduled_date=visit_date,
        time_slot=time_slot,
        status="scheduled",
    )
    db.add(new_visit)
    db.commit()

    from app.services.notifications import send_notification
    send_notification(
        db,
        user_id,
        f"A technician ({chosen_tech.name}) has been scheduled for {visit_date.strftime('%A, %B %d')} ({time_slot}). Ticket ID: {ticket_id}.",
    )
    return f"Success! Ticket {ticket_id} created. A technician named {chosen_tech.name} is scheduled for {visit_date.strftime('%A, %B %d')} during the {time_slot}."
def get_payment_history(db: Session, user_id: str) -> str:
    
    """Returns the last 5 payment transactions for the user."""
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == uuid.UUID(user_id))
        .order_by(Payment.created_at.desc())
        .limit(5)
        .all()
    )
    
    if not payments:
        return "No payment history found for your account."
        
    history_str = "Here are your recent payments:\n"
    for p in payments:
        date_str = p.created_at.strftime("%Y-%m-%d")
        history_str += f"- {date_str}: {p.amount} TND ({p.method}) - Status: {p.status}\n"
        
    return history_str.strip()