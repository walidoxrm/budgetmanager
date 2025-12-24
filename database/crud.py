from sqlalchemy.orm import Session
from database.models import TransactionModel, BudgetModel
from models.transaction import TransactionCreate
from models.budget import BudgetCreate, BudgetUpdate
from datetime import datetime

def create_transaction(db: Session, transaction: TransactionCreate):
    """Crée une nouvelle transaction"""
    db_transaction = TransactionModel(
        description=transaction.description,
        amount=transaction.amount,
        category=transaction.category,
        date=transaction.date
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_all_transactions(db: Session):
    """Récupère toutes les transactions"""
    return db.query(TransactionModel).all()

def get_transactions_by_month(db: Session, month: int, year: int):
    """Récupère les transactions d'un mois spécifique"""
    return db.query(TransactionModel).filter(
        TransactionModel.date.like(f"{year}-{month:02d}%")
    ).all()

def delete_all_transactions(db: Session):
    """Supprime toutes les transactions"""
    count = db.query(TransactionModel).delete()
    db.commit()
    return count

def get_transaction_by_id(db: Session, transaction_id: int):
    """Récupère une transaction par son ID"""
    return db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()

def update_transaction_category(db: Session, transaction_id: int, category: str):
    """Met à jour la catégorie d'une transaction"""
    transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not transaction:
        return None
    transaction.category = category
    db.commit()
    db.refresh(transaction)
    return transaction

def update_transaction_description(db: Session, transaction_id: int, description: str):
    """Met à jour la description d'une transaction"""
    transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not transaction:
        return None
    transaction.description = description
    db.commit()
    db.refresh(transaction)
    return transaction

def delete_transaction(db: Session, transaction_id: int):
    """Supprime une transaction"""
    transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True

# Budget CRUD functions
def create_budget(db: Session, budget: BudgetCreate):
    """Crée ou met à jour un budget pour une catégorie"""
    existing = db.query(BudgetModel).filter(
        BudgetModel.category == budget.category,
        BudgetModel.month == budget.month,
        BudgetModel.year == budget.year
    ).first()
    
    if existing:
        existing.amount = budget.amount
        db.commit()
        db.refresh(existing)
        return existing
    else:
        db_budget = BudgetModel(
            category=budget.category,
            amount=budget.amount,
            month=budget.month,
            year=budget.year
        )
        db.add(db_budget)
        db.commit()
        db.refresh(db_budget)
        return db_budget

def get_budget(db: Session, category: str, month: int, year: int):
    """Récupère un budget spécifique"""
    return db.query(BudgetModel).filter(
        BudgetModel.category == category,
        BudgetModel.month == month,
        BudgetModel.year == year
    ).first()

def get_all_budgets(db: Session, month: int = None, year: int = None):
    """Récupère tous les budgets, optionnellement filtrés par mois/année"""
    query = db.query(BudgetModel)
    if month and year:
        query = query.filter(
            BudgetModel.month == month,
            BudgetModel.year == year
        )
    return query.all()

def update_budget(db: Session, budget_id: int, budget_update: BudgetUpdate):
    """Met à jour un budget"""
    budget = db.query(BudgetModel).filter(BudgetModel.id == budget_id).first()
    if not budget:
        return None
    
    if budget_update.amount is not None:
        budget.amount = budget_update.amount
    if budget_update.month is not None:
        budget.month = budget_update.month
    if budget_update.year is not None:
        budget.year = budget_update.year
    
    db.commit()
    db.refresh(budget)
    return budget

def delete_budget(db: Session, budget_id: int):
    """Supprime un budget"""
    budget = db.query(BudgetModel).filter(BudgetModel.id == budget_id).first()
    if not budget:
        return False
    db.delete(budget)
    db.commit()
    return True

