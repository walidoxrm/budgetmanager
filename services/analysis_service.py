from typing import List, Dict
from collections import defaultdict
from datetime import datetime

class AnalysisService:
    def __init__(self):
        # Seuils pour les alertes (en pourcentage du budget total)
        self.alert_thresholds = {
            'high': 0.15,  # 15% du budget total
            'medium': 0.10  # 10% du budget total
        }
    
    def analyze_expenses(self, transactions: List[Dict]) -> Dict:
        """
        Analyse les dépenses et génère des suggestions d'économies
        """
        if not transactions:
            return {
                'total': 0,
                'by_category': {},
                'suggestions': []
            }
        
        # Calculer le total
        total = sum(t['amount'] for t in transactions)
        
        # Grouper par catégorie
        by_category = defaultdict(float)
        category_count = defaultdict(int)
        
        for transaction in transactions:
            category = transaction.get('category', 'Autres')
            by_category[category] += transaction['amount']
            category_count[category] += 1
        
        # Convertir en dict normal
        by_category_dict = dict(by_category)
        
        # Calculer les pourcentages
        category_percentages = {
            cat: (amount / total * 100) if total > 0 else 0
            for cat, amount in by_category_dict.items()
        }
        
        # Générer des suggestions
        suggestions = self._generate_suggestions(
            by_category_dict,
            category_percentages,
            total,
            category_count
        )
        
        # Trouver la catégorie la plus dépensière
        top_category = max(by_category_dict.items(), key=lambda x: x[1]) if by_category_dict else None
        
        return {
            'total': round(total, 2),
            'by_category': {k: round(v, 2) for k, v in by_category_dict.items()},
            'category_percentages': {k: round(v, 2) for k, v in category_percentages.items()},
            'top_category': {
                'name': top_category[0] if top_category else None,
                'amount': round(top_category[1], 2) if top_category else 0,
                'percentage': round(category_percentages.get(top_category[0], 0), 2) if top_category else 0
            },
            'transaction_count': len(transactions),
            'average_transaction': round(total / len(transactions), 2) if transactions else 0,
            'suggestions': suggestions
        }
    
    def _generate_suggestions(self, by_category: Dict, percentages: Dict, total: float, counts: Dict) -> List[Dict]:
        """
        Génère des suggestions d'économies basées sur l'analyse
        """
        suggestions = []
        
        # Suggestion 1: Catégorie avec le plus de dépenses
        if by_category:
            top_cat = max(by_category.items(), key=lambda x: x[1])
            if top_cat[1] > total * 0.20:  # Plus de 20% du budget
                suggestions.append({
                    'type': 'warning',
                    'title': f'Attention: {top_cat[0]} représente {percentages[top_cat[0]]:.1f}% de vos dépenses',
                    'message': f'Vous avez dépensé {top_cat[1]:.2f}€ dans cette catégorie. Pensez à comparer les prix ou réduire certaines dépenses.',
                    'potential_savings': f'Jusqu\'à {top_cat[1] * 0.1:.2f}€ par mois'
                })
        
        # Suggestion 2: Alimentation (incluant Restaurant et Boulangerie)
        alimentation_total = (
            by_category.get('Alimentation', 0) +
            by_category.get('Restaurant', 0) +
            by_category.get('Boulangerie', 0)
        )
        if alimentation_total > 400:  # Plus de 400€/mois
            suggestions.append({
                'type': 'info',
                'title': 'Optimisation des dépenses alimentaires',
                'message': f'Vous dépensez {alimentation_total:.2f}€ en alimentation (courses, restaurants, boulangeries). Pensez aux promotions, aux marques distributeur et à cuisiner plus souvent.',
                'potential_savings': f'Jusqu\'à {alimentation_total * 0.15:.2f}€ par mois'
            })
        
        # Suggestion spécifique pour les restaurants
        if 'Restaurant' in by_category:
            restaurant = by_category['Restaurant']
            if restaurant > 200:  # Plus de 200€/mois en restaurants
                suggestions.append({
                    'type': 'tip',
                    'title': 'Réduction des sorties au restaurant',
                    'message': f'Vous dépensez {restaurant:.2f}€ en restaurants. Cuisiner à la maison peut vous faire économiser significativement.',
                    'potential_savings': f'Jusqu\'à {restaurant * 0.4:.2f}€ par mois'
                })
        
        # Suggestion 3: Abonnements multiples
        if 'Abonnements' in by_category:
            abonnements = by_category['Abonnements']
            if abonnements > 50:
                suggestions.append({
                    'type': 'tip',
                    'title': 'Révision des abonnements',
                    'message': f'Vous avez {abonnements:.2f}€ d\'abonnements. Vérifiez ceux que vous utilisez vraiment et annulez les autres.',
                    'potential_savings': f'Jusqu\'à {abonnements * 0.3:.2f}€ par mois'
                })
        
        # Suggestion 4: Transport
        if 'Transport' in by_category:
            transport = by_category['Transport']
            if transport > 200:
                suggestions.append({
                    'type': 'tip',
                    'title': 'Optimisation des déplacements',
                    'message': f'Vous dépensez {transport:.2f}€ en transport. Pensez au covoiturage, aux transports en commun ou au vélo pour les trajets courts.',
                    'potential_savings': f'Jusqu\'à {transport * 0.2:.2f}€ par mois'
                })
        
        # Suggestion 5: Shopping excessif
        if 'Shopping' in by_category:
            shopping = by_category['Shopping']
            if shopping > 300:
                suggestions.append({
                    'type': 'warning',
                    'title': 'Dépenses shopping élevées',
                    'message': f'Vous avez dépensé {shopping:.2f}€ en shopping. Attendez 24h avant d\'acheter pour éviter les achats impulsifs.',
                    'potential_savings': f'Jusqu\'à {shopping * 0.25:.2f}€ par mois'
                })
        
        # Suggestion générale si total élevé
        if total > 2000:
            suggestions.append({
                'type': 'info',
                'title': 'Budget mensuel élevé',
                'message': f'Vos dépenses totales sont de {total:.2f}€. Pensez à établir un budget mensuel et à suivre vos dépenses régulièrement.',
                'potential_savings': 'Variable selon vos objectifs'
            })
        
        return suggestions

