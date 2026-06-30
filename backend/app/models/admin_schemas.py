from pydantic import BaseModel


class OutageCreate(BaseModel):
    city: str
    status: str


class TicketStatusUpdate(BaseModel):
    status: str


class VisitUpdate(BaseModel):
    scheduled_date: str
    time_slot: str
    technician_id: str


class CommentCreate(BaseModel):
    content: str