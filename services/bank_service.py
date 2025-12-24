"""
Service pour intégrer les APIs bancaires et récupérer les transactions
Supporte Plaid (principal) et d'autres services
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Support Plaid
try:
    import plaid
    from plaid.api import plaid_api
    from plaid.configuration import Configuration
    from plaid.api_client import ApiClient
    PLAID_AVAILABLE = True
except ImportError:
    PLAID_AVAILABLE = False
    logger.warning("Plaid n'est pas installé. Installez-le avec: pip install plaid-python")

class BankService:
    """Service pour récupérer les transactions depuis les APIs bancaires"""
    
    def __init__(self):
        self.plaid_client = None
        if PLAID_AVAILABLE:
            self._init_plaid()
    
    def _init_plaid(self):
        """Initialise le client Plaid"""
        try:
            plaid_client_id = os.getenv('PLAID_CLIENT_ID')
            plaid_secret = os.getenv('PLAID_SECRET')
            plaid_env = os.getenv('PLAID_ENV', 'sandbox')  # sandbox, development, production
            
            if not plaid_client_id or not plaid_secret:
                logger.warning("Plaid credentials non configurées. Configurez PLAID_CLIENT_ID et PLAID_SECRET")
                return
            
            # Mapping des environnements Plaid (utiliser getattr pour accéder aux attributs)
            env_mapping = {
                'sandbox': getattr(plaid.Environment, 'Sandbox', None),
                'development': getattr(plaid.Environment, 'Development', None),
                'production': getattr(plaid.Environment, 'Production', None)
            }
            
            plaid_host = env_mapping.get(plaid_env.lower())
            if not plaid_host:
                logger.warning(f"Environnement Plaid '{plaid_env}' non reconnu, utilisation de Sandbox")
                plaid_host = getattr(plaid.Environment, 'Sandbox', None)
            
            if not plaid_host:
                logger.error("Impossible d'accéder à l'environnement Plaid")
                return
            
            configuration = Configuration(
                host=plaid_host,
                api_key={
                    'clientId': plaid_client_id,
                    'secret': plaid_secret
                }
            )
            
            api_client = ApiClient(configuration)
            self.plaid_client = plaid_api.PlaidApi(api_client)
            logger.info("Plaid client initialisé")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de Plaid: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            self.plaid_client = None
    
    def get_transactions_from_plaid(
        self, 
        access_token: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Récupère les transactions depuis Plaid
        
        Args:
            access_token: Token d'accès Plaid (obtenu après connexion bancaire)
            start_date: Date de début (défaut: il y a 30 jours)
            end_date: Date de fin (défaut: aujourd'hui)
        
        Returns:
            Liste de transactions au format standardisé
        """
        if not self.plaid_client:
            raise Exception("Plaid n'est pas configuré")
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        try:
            request = {
                'access_token': access_token,
                'start_date': start_date.date(),
                'end_date': end_date.date()
            }
            
            response = self.plaid_client.transactions_get(request)
            transactions = response['transactions']
            
            # Convertir au format standardisé
            formatted_transactions = []
            for txn in transactions:
                # Ignorer les transactions en attente si nécessaire
                if txn.get('pending', False):
                    continue
                
                formatted_transactions.append({
                    'description': txn.get('name', txn.get('merchant_name', 'Transaction inconnue')),
                    'amount': abs(txn.get('amount', 0)),  # Plaid retourne des montants positifs pour les débits
                    'date': txn.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'category': None,  # Sera catégorisé par le service de catégorisation
                    'source': 'plaid',
                    'transaction_id': txn.get('transaction_id')
                })
            
            return formatted_transactions
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions Plaid: {str(e)}")
            raise
    
    def create_link_token(self, user_id: str) -> Dict:
        """
        Crée un token de lien pour initialiser le flux Plaid Link
        
        Args:
            user_id: Identifiant unique de l'utilisateur
        
        Returns:
            Dictionnaire avec le link_token
        """
        if not self.plaid_client:
            raise Exception("Plaid n'est pas configuré")
        
        try:
            request = {
                'user': {
                    'client_user_id': user_id
                },
                'client_name': 'Gestion Dépenses',
                'products': ['transactions'],
                'country_codes': ['FR'],  # France
                'language': 'fr'
            }
            
            response = self.plaid_client.link_token_create(request)
            return {
                'link_token': response['link_token'],
                'expiration': response['expiration']
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création du link token: {str(e)}")
            raise
    
    def exchange_public_token(self, public_token: str) -> str:
        """
        Échange un public_token contre un access_token
        
        Args:
            public_token: Token public obtenu depuis Plaid Link
        
        Returns:
            access_token pour les requêtes futures
        """
        if not self.plaid_client:
            raise Exception("Plaid n'est pas configuré")
        
        try:
            request = {'public_token': public_token}
            response = self.plaid_client.item_public_token_exchange(request)
            return response['access_token']
        except Exception as e:
            logger.error(f"Erreur lors de l'échange du token: {str(e)}")
            raise

