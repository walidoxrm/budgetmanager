from sqlalchemy import Column, Integer, String, Float, Date
from database.database import Base

class TransactionModel(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, index=True)
    amount = Column(Float)
    category = Column(String, index=True)
    date = Column(String)

class BudgetModel(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True)
    amount = Column(Float)
    month = Column(Integer)  # 1-12
    year = Column(Integer)  # ex: 2025

