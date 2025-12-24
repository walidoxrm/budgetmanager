from pydantic import BaseModel
from typing import Optional

class BudgetBase(BaseModel):
    category: str
    amount: float
    month: int
    year: int

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    month: Optional[int] = None
    year: Optional[int] = None

class Budget(BudgetBase):
    id: int
    
    class Config:
        from_attributes = True

