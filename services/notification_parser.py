"""
Service pour parser les notifications de paiement (SMS, Email)
Utile pour récupérer les transactions depuis les notifications bancaires
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationParser:
    """Parse les notifications de paiement pour extraire les transactions"""
    
    def __init__(self):
        # Patterns pour différents types de notifications bancaires françaises
        self.patterns = {
            'carte': [
                # Format: "CARTE XXXX 1234 - 15.50 EUR - CARREFOUR - 12/01/2024"
                r'(?:CARTE|CARTE\s+\*\*\*\*)\s+(?:\d{4}|XXXX)\s*[-–]\s*([\d,\.]+)\s*(?:EUR|€|EUROS?)\s*[-–]\s*([^-]+?)\s*[-–]\s*(\d{2}/\d{2}/\d{4})',
                # Format: "Paiement CARTE 15.50€ CARREFOUR le 12/01/2024"
                r'Paiement\s+(?:CARTE|CB)\s+([\d,\.]+)[€EUR\s]+([^-]+?)\s+(?:le\s+)?(\d{2}/\d{2}/\d{4})',
            ],
            'virement': [
                # Format: "Virement reçu de 100.00 EUR - 12/01/2024"
                r'Virement\s+(?:reçu|envoyé)\s+(?:de|vers)?\s+([\d,\.]+)\s*(?:EUR|€)\s*[-–]\s*([^-]+?)?\s*[-–]?\s*(\d{2}/\d{2}/\d{4})?',
            ],
            'prelevement': [
                # Format: "Prélèvement 25.00 EUR - ABONNEMENT - 12/01/2024"
                r'Pr[ée]l[èe]vement\s+([\d,\.]+)\s*(?:EUR|€)\s*[-–]\s*([^-]+?)\s*[-–]\s*(\d{2}/\d{2}/\d{4})',
            ]
        }
    
    def parse_sms(self, sms_text: str, sms_date: Optional[str] = None) -> Optional[Dict]:
        """
        Parse un SMS de notification bancaire
        
        Args:
            sms_text: Texte du SMS
            sms_date: Date du SMS (format YYYY-MM-DD), si None utilise aujourd'hui
        
        Returns:
            Transaction parsée ou None si le format n'est pas reconnu
        """
        if not sms_text:
            return None
        
        sms_text = sms_text.strip().upper()
        
        # Essayer chaque pattern
        for transaction_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, sms_text, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '.')
                        amount = float(amount_str)
                        
                        description = match.group(2).strip() if match.group(2) else "Transaction"
                        
                        # Parser la date
                        if match.lastindex >= 3 and match.group(3):
                            date_str = match.group(3)
                            # Format DD/MM/YYYY ou DD/MM/YY
                            if '/' in date_str:
                                parts = date_str.split('/')
                                if len(parts) == 3:
                                    day, month, year = parts
                                    if len(year) == 2:
                                        year = '20' + year
                                    date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                else:
                                    date = sms_date or datetime.now().strftime('%Y-%m-%d')
                            else:
                                date = sms_date or datetime.now().strftime('%Y-%m-%d')
                        else:
                            date = sms_date or datetime.now().strftime('%Y-%m-%d')
                        
                        return {
                            'description': description,
                            'amount': amount,
                            'date': date,
                            'category': None,  # Sera catégorisé plus tard
                            'source': 'sms',
                            'type': transaction_type
                        }
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Erreur lors du parsing du SMS: {str(e)}")
                        continue
        
        return None
    
    def parse_email(self, email_subject: str, email_body: str, email_date: Optional[str] = None) -> Optional[Dict]:
        """
        Parse un email de notification bancaire
        
        Args:
            email_subject: Sujet de l'email
            email_body: Corps de l'email
            email_date: Date de l'email (format YYYY-MM-DD)
        
        Returns:
            Transaction parsée ou None
        """
        # Combiner sujet et corps pour le parsing
        full_text = f"{email_subject} {email_body}"
        
        # Utiliser la même logique que pour les SMS
        return self.parse_sms(full_text, email_date)
    
    def parse_multiple_sms(self, sms_list: List[Dict]) -> List[Dict]:
        """
        Parse une liste de SMS
        
        Args:
            sms_list: Liste de dictionnaires avec 'text' et optionnellement 'date'
        
        Returns:
            Liste de transactions parsées
        """
        transactions = []
        for sms in sms_list:
            parsed = self.parse_sms(
                sms.get('text', ''),
                sms.get('date')
            )
            if parsed:
                transactions.append(parsed)
        
        return transactions

