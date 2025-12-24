from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uvicorn
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from services.ocr_service import OCRService
from services.categorization_service import CategorizationService
from services.analysis_service import AnalysisService
from services.bank_service import BankService
from services.notification_parser import NotificationParser
from database.database import init_db, get_db
from models.transaction import Transaction, TransactionCreate
from database.crud import (
    create_transaction, get_all_transactions, get_transactions_by_month, 
    delete_all_transactions, update_transaction_category, update_transaction_description, 
    get_transaction_by_id, delete_transaction,
    create_budget, get_budget, get_all_budgets, update_budget, delete_budget
)
from models.budget import BudgetCreate, BudgetUpdate
from models.bank_connection import (
    LinkTokenRequest, LinkTokenResponse,
    ExchangeTokenRequest, ExchangeTokenResponse,
    SMSNotificationRequest, EmailNotificationRequest,
    SyncTransactionsRequest
)

load_dotenv()

app = FastAPI(title="Gestion Dépenses API", version="1.0.0")

# CORS middleware
# Autoriser toutes les origines pour le développement local (y compris iPhone sur le même réseau)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En développement, autoriser toutes les origines
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize database
init_db()

# Initialize services
ocr_service = OCRService()
categorization_service = CategorizationService()
analysis_service = AnalysisService()
bank_service = BankService()
notification_parser = NotificationParser()

@app.get("/")
async def root():
    return {"message": "Gestion Dépenses API"}

@app.post("/api/upload-releve")
async def upload_releve(files: List[UploadFile] = File(...)):
    """
    Upload et traitement des photos de relevé de compte
    """
    try:
        all_transactions = []
        errors = []
        
        for file in files:
            try:
                # Vérifier le type de fichier (image ou PDF)
                is_pdf = False
                if not file.content_type:
                    # Essayer de deviner depuis l'extension
                    if file.filename.lower().endswith('.pdf'):
                        is_pdf = True
                    elif not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        errors.append(f"Le fichier {file.filename} n'est pas un format supporté (JPG, PNG, PDF)")
                        continue
                elif file.content_type == 'application/pdf':
                    is_pdf = True
                elif not file.content_type.startswith('image/'):
                    errors.append(f"Le fichier {file.filename} n'est pas une image ou un PDF valide")
                    continue
                
                # Lire le contenu du fichier
                contents = await file.read()
                
                if not contents or len(contents) == 0:
                    errors.append(f"Le fichier {file.filename} est vide")
                    continue
                
                # Extraire le texte avec OCR
                try:
                    extracted_text = ocr_service.extract_text(contents, is_pdf=is_pdf)
                except Exception as ocr_error:
                    error_msg = str(ocr_error)
                    # Messages plus spécifiques pour les images WhatsApp
                    if 'whatsapp' in file.filename.lower() or 'wa' in file.filename.lower():
                        errors.append(
                            f"Erreur OCR pour {file.filename}:\n"
                            f"Les images WhatsApp sont souvent compressées ou corrompues.\n"
                            f"💡 Solution: Sauvegardez l'image depuis WhatsApp, puis ré-uploadez le fichier sauvegardé.\n"
                            f"Erreur technique: {error_msg[:150]}"
                        )
                    else:
                        errors.append(f"Erreur OCR pour {file.filename}: {error_msg}")
                    continue
                
                # Parser les transactions
                transactions = ocr_service.parse_transactions(extracted_text)
                
                if not transactions:
                    errors.append(f"Aucune transaction trouvée dans {file.filename}. Vérifiez que l'image est claire et contient des relevés bancaires.")
                    continue
                
                # Catégoriser chaque transaction
                for transaction in transactions:
                    transaction['category'] = categorization_service.categorize(transaction['description'])
                    transaction['date'] = datetime.now().strftime('%Y-%m-%d') if 'date' not in transaction else transaction['date']
                    
                    # Sauvegarder en base de données
                    db = next(get_db())
                    transaction_db = create_transaction(db, TransactionCreate(**transaction))
                    all_transactions.append({
                        'id': transaction_db.id,
                        'description': transaction_db.description,
                        'amount': transaction_db.amount,
                        'category': transaction_db.category,
                        'date': transaction_db.date
                    })
            
            except Exception as file_error:
                errors.append(f"Erreur lors du traitement de {file.filename}: {str(file_error)}")
                continue
        
        # Si aucune transaction n'a été extraite et qu'il y a des erreurs
        if not all_transactions and errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Aucune transaction n'a pu être extraite",
                    "errors": errors,
                    "suggestions": [
                        "Vérifiez que les images sont claires et bien éclairées",
                        "Assurez-vous que les relevés bancaires sont complets",
                        "Vérifiez que Tesseract est correctement installé avec les données de langue françaises"
                    ]
                }
            )
        
        response = {
            "success": True,
            "transactions": all_transactions,
            "count": len(all_transactions)
        }
        
        if errors:
            response["warnings"] = errors
        
        return JSONResponse(response)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/api/transactions")
async def get_transactions(month: int = None, year: int = None):
    """
    Récupérer toutes les transactions, optionnellement filtrées par mois/année
    """
    try:
        db = next(get_db())
        if month and year:
            transactions = get_transactions_by_month(db, month, year)
        else:
            transactions = get_all_transactions(db)
        
        return JSONResponse({
            "success": True,
            "transactions": [{
                'id': t.id,
                'description': t.description,
                'amount': t.amount,
                'category': t.category,
                'date': t.date
            } for t in transactions]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis")
async def get_analysis(month: int = None, year: int = None):
    """
    Obtenir l'analyse des dépenses et suggestions d'économies
    """
    try:
        db = next(get_db())
        if month and year:
            transactions = get_transactions_by_month(db, month, year)
        else:
            transactions = get_all_transactions(db)
        
        if not transactions:
            return JSONResponse({
                "success": True,
                "message": "Aucune transaction trouvée",
                "analysis": {
                    'total': 0,
                    'by_category': {},
                    'category_percentages': {},
                    'top_category': {
                        'name': 'N/A',
                        'amount': 0,
                        'percentage': 0
                    },
                    'transaction_count': 0,
                    'average_transaction': 0,
                    'suggestions': []
                }
            })
        
        # Convertir en format pour l'analyse
        transactions_data = [{
            'description': t.description,
            'amount': t.amount,
            'category': t.category,
            'date': t.date
        } for t in transactions]
        
        analysis = analysis_service.analyze_expenses(transactions_data)
        
        return JSONResponse({
            "success": True,
            "analysis": analysis
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reset")
async def delete_all_transactions_endpoint():
    """
    Supprime toutes les transactions (réinitialisation)
    """
    try:
        db = next(get_db())
        count = delete_all_transactions(db)
        
        return JSONResponse({
            "success": True,
            "message": f"{count} transaction(s) supprimée(s)",
            "count": count
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/transactions/{transaction_id}/category")
async def update_transaction_category_endpoint(
    transaction_id: int, 
    category: str = Query(..., description="Nouvelle catégorie")
):
    """
    Met à jour la catégorie d'une transaction
    """
    try:
        db = next(get_db())
        
        # Vérifier que la transaction existe
        transaction = get_transaction_by_id(db, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction non trouvée")
        
        # Valider la catégorie
        valid_categories = [
            'Alimentation', 'Restaurant', 'Boulangerie', 'Station de service', 'Transport', 
            'Logement', 'Santé', 'Shopping', 'Loisirs', 'Abonnements', 'Banque', 'Autres'
        ]
        if category not in valid_categories:
            raise HTTPException(
                status_code=400, 
                detail=f"Catégorie invalide. Catégories valides: {', '.join(valid_categories)}"
            )
        
        # Mettre à jour
        updated_transaction = update_transaction_category(db, transaction_id, category)
        
        return JSONResponse({
            "success": True,
            "transaction": {
                'id': updated_transaction.id,
                'description': updated_transaction.description,
                'amount': updated_transaction.amount,
                'category': updated_transaction.category,
                'date': updated_transaction.date
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/transactions/{transaction_id}/description")
async def update_transaction_description_endpoint(
    transaction_id: int, 
    description: str = Query(..., description="Nouvelle description")
):
    """
    Met à jour la description d'une transaction
    """
    try:
        db = next(get_db())
        
        # Vérifier que la transaction existe
        transaction = get_transaction_by_id(db, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction non trouvée")
        
        if not description or len(description.strip()) == 0:
            raise HTTPException(status_code=400, detail="La description ne peut pas être vide")
        
        # Mettre à jour
        updated_transaction = update_transaction_description(db, transaction_id, description.strip())
        
        return JSONResponse({
            "success": True,
            "transaction": {
                'id': updated_transaction.id,
                'description': updated_transaction.description,
                'amount': updated_transaction.amount,
                'category': updated_transaction.category,
                'date': updated_transaction.date
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction_endpoint(transaction_id: int):
    """
    Supprime une transaction spécifique
    """
    try:
        db = next(get_db())
        
        # Vérifier que la transaction existe
        transaction = get_transaction_by_id(db, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction non trouvée")
        
        # Supprimer la transaction
        success = delete_transaction(db, transaction_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression")
        
        return JSONResponse({
            "success": True,
            "message": "Transaction supprimée avec succès"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Budget endpoints
@app.post("/api/budgets")
async def create_budget_endpoint(budget: BudgetCreate):
    """
    Crée ou met à jour un budget pour une catégorie
    """
    try:
        db = next(get_db())
        db_budget = create_budget(db, budget)
        return JSONResponse({
            "success": True,
            "budget": {
                'id': db_budget.id,
                'category': db_budget.category,
                'amount': db_budget.amount,
                'month': db_budget.month,
                'year': db_budget.year
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets")
async def get_budgets_endpoint(month: Optional[int] = None, year: Optional[int] = None):
    """
    Récupère tous les budgets, optionnellement filtrés par mois/année
    """
    try:
        db = next(get_db())
        budgets = get_all_budgets(db, month, year)
        return JSONResponse({
            "success": True,
            "budgets": [{
                'id': b.id,
                'category': b.category,
                'amount': b.amount,
                'month': b.month,
                'year': b.year
            } for b in budgets]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets/summary")
async def get_budgets_summary(month: Optional[int] = None, year: Optional[int] = None):
    """
    Récupère un résumé des budgets avec les dépenses réelles et le reste
    """
    try:
        db = next(get_db())
        
        # Utiliser le mois/année actuel si non spécifié
        if not month or not year:
            now = datetime.now()
            month = month or now.month
            year = year or now.year
        
        # Récupérer les budgets
        budgets = get_all_budgets(db, month, year)
        
        # Récupérer les transactions du mois
        transactions = get_transactions_by_month(db, month, year)
        
        # Calculer les dépenses par catégorie
        expenses_by_category = {}
        for transaction in transactions:
            category = transaction.category
            if category not in expenses_by_category:
                expenses_by_category[category] = 0
            expenses_by_category[category] += transaction.amount
        
        # Créer le résumé
        summary = []
        for budget in budgets:
            spent = expenses_by_category.get(budget.category, 0)
            remaining = budget.amount - spent
            percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
            
            summary.append({
                'id': budget.id,
                'category': budget.category,
                'budget': budget.amount,
                'spent': round(spent, 2),
                'remaining': round(remaining, 2),
                'percentage': round(percentage, 2)
            })
        
        return JSONResponse({
            "success": True,
            "month": month,
            "year": year,
            "summary": summary
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/budgets/{budget_id}")
async def update_budget_endpoint(budget_id: int, budget_update: BudgetUpdate):
    """
    Met à jour un budget
    """
    try:
        db = next(get_db())
        updated_budget = update_budget(db, budget_id, budget_update)
        if not updated_budget:
            raise HTTPException(status_code=404, detail="Budget non trouvé")
        
        return JSONResponse({
            "success": True,
            "budget": {
                'id': updated_budget.id,
                'category': updated_budget.category,
                'amount': updated_budget.amount,
                'month': updated_budget.month,
                'year': updated_budget.year
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/budgets/{budget_id}")
async def delete_budget_endpoint(budget_id: int):
    """
    Supprime un budget
    """
    try:
        db = next(get_db())
        success = delete_budget(db, budget_id)
        if not success:
            raise HTTPException(status_code=404, detail="Budget non trouvé")
        
        return JSONResponse({
            "success": True,
            "message": "Budget supprimé avec succès"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transactions/manual")
async def create_manual_transaction(transaction: TransactionCreate):
    """
    Crée une transaction manuellement (pour l'ajout mobile)
    """
    try:
        db = next(get_db())
        transaction_db = create_transaction(db, transaction)
        return JSONResponse({
            "success": True,
            "transaction": {
                'id': transaction_db.id,
                'description': transaction_db.description,
                'amount': transaction_db.amount,
                'category': transaction_db.category,
                'date': transaction_db.date
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bank integration endpoints
@app.post("/api/bank/link-token", response_model=LinkTokenResponse)
async def create_link_token(request: LinkTokenRequest):
    """
    Crée un token de lien Plaid pour initialiser la connexion bancaire
    """
    try:
        result = bank_service.create_link_token(request.user_id)
        return LinkTokenResponse(**result)
    except Exception as e:
        logger.error(f"Erreur lors de la création du link token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/bank/exchange-token", response_model=ExchangeTokenResponse)
async def exchange_public_token(request: ExchangeTokenRequest):
    """
    Échange un public_token contre un access_token
    """
    try:
        access_token = bank_service.exchange_public_token(request.public_token)
        return ExchangeTokenResponse(
            access_token=access_token,
            item_id=""  # Plaid retourne aussi un item_id, à récupérer si nécessaire
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'échange du token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/bank/sync-transactions")
async def sync_transactions(request: SyncTransactionsRequest):
    """
    Synchronise les transactions depuis Plaid
    """
    try:
        from datetime import datetime as dt
        
        start_date = None
        end_date = None
        
        if request.start_date:
            start_date = dt.strptime(request.start_date, '%Y-%m-%d')
        if request.end_date:
            end_date = dt.strptime(request.end_date, '%Y-%m-%d')
        
        transactions = bank_service.get_transactions_from_plaid(
            request.access_token,
            start_date,
            end_date
        )
        
        # Catégoriser et sauvegarder les transactions
        db = next(get_db())
        saved_transactions = []
        
        for transaction in transactions:
            # Catégoriser
            transaction['category'] = categorization_service.categorize(transaction['description'])
            
            # Vérifier si la transaction existe déjà (par transaction_id si disponible)
            # Pour éviter les doublons
            if transaction.get('transaction_id'):
                # TODO: Implémenter la vérification de doublons
                pass
            
            # Sauvegarder
            transaction_db = create_transaction(db, TransactionCreate(**transaction))
            saved_transactions.append({
                'id': transaction_db.id,
                'description': transaction_db.description,
                'amount': transaction_db.amount,
                'category': transaction_db.category,
                'date': transaction_db.date
            })
        
        return JSONResponse({
            "success": True,
            "count": len(saved_transactions),
            "transactions": saved_transactions
        })
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# Notification parsing endpoints
@app.post("/api/notifications/parse-sms")
async def parse_sms_notification(request: SMSNotificationRequest):
    """
    Parse un SMS de notification bancaire et crée une transaction si détectée
    """
    try:
        parsed = notification_parser.parse_sms(request.text, request.date)
        
        if not parsed:
            return JSONResponse({
                "success": False,
                "message": "Aucune transaction détectée dans le SMS"
            })
        
        # Catégoriser
        parsed['category'] = categorization_service.categorize(parsed['description'])
        
        # Sauvegarder
        db = next(get_db())
        transaction_db = create_transaction(db, TransactionCreate(**parsed))
        
        return JSONResponse({
            "success": True,
            "transaction": {
                'id': transaction_db.id,
                'description': transaction_db.description,
                'amount': transaction_db.amount,
                'category': transaction_db.category,
                'date': transaction_db.date
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors du parsing SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/api/notifications/parse-email")
async def parse_email_notification(request: EmailNotificationRequest):
    """
    Parse un email de notification bancaire et crée une transaction si détectée
    """
    try:
        parsed = notification_parser.parse_email(
            request.subject,
            request.body,
            request.date
        )
        
        if not parsed:
            return JSONResponse({
                "success": False,
                "message": "Aucune transaction détectée dans l'email"
            })
        
        # Catégoriser
        parsed['category'] = categorization_service.categorize(parsed['description'])
        
        # Sauvegarder
        db = next(get_db())
        transaction_db = create_transaction(db, TransactionCreate(**parsed))
        
        return JSONResponse({
            "success": True,
            "transaction": {
                'id': transaction_db.id,
                'description': transaction_db.description,
                'amount': transaction_db.amount,
                'category': transaction_db.category,
                'date': transaction_db.date
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors du parsing email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

