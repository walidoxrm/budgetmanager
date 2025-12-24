import re
from typing import Dict

class CategorizationService:
    def __init__(self):
        # Catégories et patterns de reconnaissance basés sur les types de commerces
        # Les patterns sont organisés par priorité (du plus spécifique au plus général)
        
        self.categories = {
            'Alimentation': {
                # Supermarchés et grandes surfaces
                'patterns': [
                    r'\b(carrefour|auchan|leclerc|intermarch[ée]|intermarche|super u|monoprix|casino|geant|e\.leclerc)\b',
                    r'\b(supermarche|supermarché|hypermarch[ée]|grande surface)\b',
                    r'\b(h market|h&m market|market)\b',
                    r'\b(epicerie|épicerie|epicerie|alimentation)\b',
                ],
                'keywords': [
                    'carrefour', 'auchan', 'leclerc', 'intermarché', 'intermarche', 'super u',
                    'monoprix', 'casino', 'geant', 'supermarche', 'supermarché', 'hypermarché',
                    'h market', 'epicerie', 'épicerie', 'alimentation', 'food', 'grocery',
                    'auchan bretigny', 'auchan brétigny'  # Cas spécifiques
                ]
            },
            'Restaurant': {
                'patterns': [
                    r'\b(cafe|café|coffee|restaurant|resto|brasserie|bistrot|bistro)\b',
                    r'\b(mcdo|mcdonald|kfc|burger|pizza|pizzeria|fast food)\b',
                    r'\b(saveurs|saveur|cuisine|gastronomie)\b',
                    r'\b(deliveroo|ubereats|just eat|takeaway|livraison)\b',
                ],
                'keywords': [
                    'cafe', 'café', 'restaurant', 'resto', 'brasserie', 'bistrot', 'bistro',
                    'mcdo', 'mcdonald', 'kfc', 'burger', 'pizza', 'pizzeria', 'fast food',
                    'saveurs', 'saveur', 'deliveroo', 'ubereats', 'just eat', 'takeaway'
                ]
            },
            'Boulangerie': {
                'patterns': [
                    r'\b(boulangerie|boulanger|boulang|patisserie|pâtisserie|tradition)\b',
                    r'\b(bakery|pain|baguette)\b',
                ],
                'keywords': [
                    'boulangerie', 'boulanger', 'boulang', 'patisserie', 'pâtisserie',
                    'tradition', 'bakery'
                ]
            },
            'Shopping': {
                'patterns': [
                    r'\b(barber|barbier|coiffeur|coiffeuse|salon|hairdresser)\b',
                    r'\b(amazon|fnac|darty|ikea|zara|decathlon|cultura)\b',
                    r'\b(leroy merlin|castorama|bricorama|bricolage|brico)\b',
                    r'\b(vêtement|vetement|habillement|mode|fashion|clothing)\b',
                ],
                'keywords': [
                    'barber', 'barbier', 'coiffeur', 'coiffeuse', 'salon', 'premium barber',
                    'amazon', 'fnac', 'darty', 'ikea', 'zara', 'decathlon', 'cultura',
                    'leroy merlin', 'castorama', 'bricorama', 'bricolage', 'brico',
                    'vêtement', 'vetement', 'habillement', 'mode', 'fashion'
                ]
            },
            'Station de service': {
                'patterns': [
                    r'\b(station.*service|station.*essence|station.*carburant)\b',
                    r'\b(relais|relais.*drapeau|relais.*route)\b',
                    r'\b(total|shell|bp|esso|mobil|avia|agip)\b',
                    r'\b(essence|carburant|gasoil|gazole|diesel)\b',
                ],
                'keywords': [
                    'station service', 'station-service', 'station essence', 'station carburant',
                    'relais', 'relais drapeau', 'relais route', 'relais autoroute',
                    'total', 'shell', 'bp', 'esso', 'mobil', 'avia', 'agip',
                    'essence', 'carburant', 'gasoil', 'gazole', 'diesel'
                ]
            },
            'Transport': {
                'patterns': [
                    r'\b(peage|péage|toll|autoroute)\b',
                    r'\b(sncf|train|metro|métro|bus|tram|rer)\b',
                    r'\b(taxi|uber|bolt|heetch|parking|park)\b',
                    r'\b(garage|réparation|reparation|mecanique|mécanique)\b',
                ],
                'keywords': [
                    'peage', 'péage', 'sncf', 'train', 'metro', 'métro', 'bus', 'taxi',
                    'uber', 'parking', 'park', 'garage', 'réparation', 'reparation'
                ]
            },
            'Logement': {
                'patterns': [
                    r'\b(loyer|charges|eau|électricité|electricite|gaz)\b',
                    r'\b(edf|engie|enedis|grdf|syndic|copropriété)\b',
                    r'\b(hotel|hôtel|airbnb|booking|logement)\b',
                ],
                'keywords': [
                    'loyer', 'charges', 'eau', 'électricité', 'electricite', 'gaz',
                    'edf', 'engie', 'enedis', 'grdf', 'syndic', 'copropriété',
                    'hotel', 'hôtel', 'airbnb', 'booking'
                ]
            },
            'Santé': {
                'patterns': [
                    r'\b(pharmacie|pharma|médecin|medecin|dentiste|opticien)\b',
                    r'\b(hopital|hôpital|clinique|mutuelle|assurance santé)\b',
                    r'\b(laboratoire|analyse|medical|médical)\b',
                ],
                'keywords': [
                    'pharmacie', 'pharma', 'médecin', 'medecin', 'dentiste', 'opticien',
                    'hopital', 'hôpital', 'clinique', 'mutuelle', 'laboratoire', 'analyse'
                ]
            },
            'Loisirs': {
                'patterns': [
                    r'\b(cinema|cinéma|netflix|spotify|disney|prime video)\b',
                    r'\b(salle de sport|gym|fitness|sport|concert|spectacle)\b',
                    r'\b(musée|musee|voyage|tourisme)\b',
                ],
                'keywords': [
                    'cinema', 'cinéma', 'netflix', 'spotify', 'disney', 'prime video',
                    'salle de sport', 'gym', 'fitness', 'sport', 'concert', 'spectacle',
                    'musée', 'musee', 'voyage', 'tourisme'
                ]
            },
            'Abonnements': {
                'patterns': [
                    r'\b(abonnement|netflix|spotify|amazon prime|disney)\b',
                    r'\b(youtube premium|apple music|deezer|canal\+)\b',
                    r'\b(orange|sfr|bouygues|free|mobile|forfait)\b',
                ],
                'keywords': [
                    'abonnement', 'netflix', 'spotify', 'amazon prime', 'disney',
                    'youtube premium', 'apple music', 'deezer', 'canal+', 'orange',
                    'sfr', 'bouygues', 'free', 'mobile', 'forfait'
                ]
            },
            'Banque': {
                'patterns': [
                    r'\b(frais bancaire|agios|commission|assurance|banque)\b',
                    r'\b(crédit|credit|prêt|pret|remboursement)\b',
                ],
                'keywords': [
                    'frais bancaire', 'agios', 'commission', 'assurance', 'banque',
                    'crédit', 'credit', 'prêt', 'pret', 'remboursement'
                ]
            }
        }
    
    def categorize(self, description: str) -> str:
        """
        Catégorise une transaction basée sur sa description
        Utilise des patterns regex et des mots-clés pour une meilleure précision
        """
        if not description:
            return 'Autres'
        
        description_lower = description.lower()
        description_upper = description.upper()
        
        # Prioriser les catégories spécifiques d'abord
        priority_order = [
            'Restaurant', 'Boulangerie', 'Shopping', 'Alimentation',
            'Station de service', 'Transport', 'Logement', 'Santé', 'Loisirs', 'Abonnements', 'Banque'
        ]
        
        # Vérifier d'abord avec les patterns regex (plus précis)
        for category in priority_order:
            if category in self.categories:
                cat_data = self.categories[category]
                # Vérifier les patterns regex
                for pattern in cat_data.get('patterns', []):
                    if re.search(pattern, description_lower, re.IGNORECASE):
                        return category
        
        # Ensuite vérifier avec les mots-clés simples
        for category in priority_order:
            if category in self.categories:
                cat_data = self.categories[category]
                for keyword in cat_data.get('keywords', []):
                    if keyword in description_lower:
                        return category
        
        # Détection spéciale pour certains commerces connus
        # Basé sur l'image fournie
        special_cases = {
            'cafe': 'Restaurant',
            'café': 'Restaurant',
            'saveurs': 'Restaurant',
            'h market': 'Alimentation',
            'tradition': 'Boulangerie',
            'barber': 'Shopping',
            'barbier': 'Shopping',
            'relais': 'Station de service',  # Relais = station de service
        }
        
        for key, cat in special_cases.items():
            if key in description_lower:
                return cat
        
        return 'Autres'

