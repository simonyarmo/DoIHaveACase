import uuid
from datetime import date as date_
from datetime import datetime

from pydantic import BaseModel


class ExpenseOut(BaseModel):
    id: uuid.UUID
    description: str
    amount: float
    date: date_
    category: str
    receipt_doc_id: uuid.UUID | None = None
    recoverable: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    date: date_
    category: str
    receipt_doc_id: uuid.UUID | None = None
    recoverable: bool = True


class ExpenseUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    date: date_ | None = None
    category: str | None = None
    receipt_doc_id: uuid.UUID | None = None
    recoverable: bool | None = None
