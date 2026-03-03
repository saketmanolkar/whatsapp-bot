from pydantic import BaseModel
from datetime import datetime

class Reminder(BaseModel):
    id: str
    reminder_text: str
    reminder_time: datetime
    reminder_status: str
    reminder_created_at: datetime
    reminder_updated_at: datetime