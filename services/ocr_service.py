import pytesseract
from PIL import Image
import io
import re
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_bytes
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pdf2image n'est pas installé. Le support PDF est désactivé.")

class OCRService:
    def __init__(self):
        # Configuration Tesseract (peut nécessiter installation système)
        # Pour macOS: brew install tesseract
        # Pour Linux: sudo apt-get install tesseract-ocr
        # Pour Windows: télécharger depuis GitHub
        
        # Vérifier les langues disponibles
        try:
            self.available_languages = self._check_available_languages()
            logger.info(f"Langues Tesseract disponibles: {self.available_languages}")
        except Exception as e:
            logger.warning(f"Impossible de vérifier les langues: {e}")
            self.available_languages = ['eng']
    
    def _check_available_languages(self) -> List[str]:
        """
        Vérifie quelles langues sont disponibles dans Tesseract
        """
        try:
            langs = pytesseract.get_languages()
            return langs
        except Exception as e:
            logger.warning(f"Impossible de vérifier les langues: {e}")
            return ['eng']  # Par défaut, au moins l'anglais devrait être disponible
    
    def _get_language_config(self) -> str:
        """
        Retourne la configuration de langue optimale
        """
        if 'fra' in self.available_languages and 'eng' in self.available_languages:
            return 'fra+eng'
        elif 'fra' in self.available_languages:
            return 'fra'
        else:
            logger.warning("Langue française non disponible, utilisation de l'anglais uniquement")
            return 'eng'
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extrait le texte d'un PDF en convertissant chaque page en image puis en utilisant OCR
        """
        if not PDF_SUPPORT:
            raise Exception("Le support PDF n'est pas disponible. Installez pdf2image: pip install pdf2image")
        
        try:
            # Convertir le PDF en images (une par page)
            images = convert_from_bytes(pdf_bytes, dpi=300)
            
            if not images:
                raise ValueError("Aucune page trouvée dans le PDF")
            
            # Extraire le texte de chaque page
            all_text = []
            for i, image in enumerate(images):
                logger.info(f"Traitement de la page {i+1}/{len(images)} du PDF")
                # Convertir en RGB si nécessaire
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Extraire le texte avec OCR
                lang_config = self._get_language_config()
                try:
                    page_text = pytesseract.image_to_string(image, lang=lang_config)
                except Exception:
                    # Fallback sur anglais si nécessaire
                    page_text = pytesseract.image_to_string(image, lang='eng')
                
                if page_text and page_text.strip():
                    all_text.append(page_text)
            
            if not all_text:
                raise ValueError("Aucun texte n'a pu être extrait du PDF")
            
            # Combiner tout le texte
            return '\n'.join(all_text)
            
        except Exception as e:
            error_msg = str(e)
            if 'pdf2image' in error_msg.lower() or 'poppler' in error_msg.lower():
                raise Exception(
                    f"Erreur lors de la conversion du PDF: {error_msg}\n"
                    f"💡 Solution: Installez poppler-utils:\n"
                    f"  macOS: brew install poppler\n"
                    f"  Linux: sudo apt-get install poppler-utils\n"
                    f"  Windows: Téléchargez depuis https://github.com/oschwartz10612/poppler-windows/releases"
                )
            raise Exception(f"Erreur lors de l'extraction du PDF: {error_msg}")
    
    def extract_text(self, image_bytes: bytes, is_pdf: bool = False) -> str:
        """
        Extrait le texte d'une image ou d'un PDF en utilisant OCR
        
        Args:
            image_bytes: Les bytes de l'image ou du PDF
            is_pdf: True si c'est un PDF, False si c'est une image
        """
        if is_pdf:
            return self.extract_text_from_pdf(image_bytes)
        
        try:
            # Valider que les bytes ne sont pas vides
            if not image_bytes or len(image_bytes) == 0:
                raise ValueError("L'image est vide ou corrompue")
            
            # Essayer de charger l'image avec différentes méthodes pour gérer les images corrompues
            image = None
            try:
                # Méthode 1: Chargement normal
                image = Image.open(io.BytesIO(image_bytes))
                # Tenter de charger les données pour vérifier la validité
                image.load()
            except Exception as e1:
                logger.warning(f"Première tentative de chargement échouée: {e1}")
                try:
                    # Méthode 2: Chargement avec PIL en mode plus tolérant
                    # Réessayer avec une nouvelle instance
                    image_bytes_io = io.BytesIO(image_bytes)
                    image = Image.open(image_bytes_io)
                    # Ne pas utiliser verify() car cela peut échouer sur des images partiellement corrompues
                    # Au lieu de cela, essayer de charger les données
                    try:
                        image.load()
                    except:
                        # Si load() échoue, essayer quand même de traiter l'image
                        logger.warning("Image partiellement corrompue, tentative de traitement quand même")
                        pass
                except Exception as e2:
                    logger.warning(f"Deuxième tentative de chargement échouée: {e2}")
                    # Méthode 3: Essayer de réparer en sauvegardant dans un nouveau buffer
                    try:
                        temp_image = Image.open(io.BytesIO(image_bytes))
                        # Sauvegarder dans un nouveau buffer pour "réparer" l'image
                        repaired_buffer = io.BytesIO()
                        temp_image.save(repaired_buffer, format='PNG', quality=95)
                        repaired_buffer.seek(0)
                        image = Image.open(repaired_buffer)
                        image.load()
                        logger.info("Image réparée avec succès")
                    except Exception as e3:
                        raise ValueError(
                            f"Impossible de lire l'image: {str(e1)}\n"
                            f"Tentatives de réparation échouées. L'image semble trop corrompue.\n"
                            f"Veuillez réessayer avec une image valide et complète."
                        )
            
            if image is None:
                raise ValueError("Impossible de charger l'image")
            
            # Convertir en RGB si nécessaire (pour les images avec transparence)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Optionnel: Améliorer la qualité de l'image pour l'OCR
            # Redimensionner si l'image est trop petite (améliore souvent l'OCR)
            width, height = image.size
            if width < 300 or height < 300:
                # Redimensionner pour améliorer la qualité OCR
                scale_factor = max(300 / width, 300 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Image redimensionnée de {width}x{height} à {new_size[0]}x{new_size[1]}")
            
            # Essayer d'abord avec français+anglais, puis fallback sur anglais seul
            lang_config = self._get_language_config()
            
            try:
                text = pytesseract.image_to_string(image, lang=lang_config)
            except Exception as lang_error:
                # Si erreur de langue, essayer avec anglais uniquement
                if 'fra' in lang_config:
                    logger.warning(f"Erreur avec la langue {lang_config}, tentative avec anglais uniquement")
                    try:
                        text = pytesseract.image_to_string(image, lang='eng')
                    except Exception as eng_error:
                        raise Exception(f"Erreur OCR même avec anglais: {str(eng_error)}")
                else:
                    raise Exception(f"Erreur lors de l'extraction OCR: {str(lang_error)}")
            
            if not text or not text.strip():
                raise ValueError("Aucun texte n'a pu être extrait de l'image. Vérifiez que l'image contient du texte lisible.")
            
            return text
            
        except ValueError as ve:
            # Erreurs de validation - on les propage telles quelles
            raise ve
        except Exception as e:
            error_msg = str(e)
            # Messages d'erreur plus clairs
            if 'tessdata' in error_msg.lower() or 'language' in error_msg.lower():
                raise Exception(
                    f"Erreur de configuration Tesseract: {error_msg}\n"
                    f"Solution: Installez les données de langue avec:\n"
                    f"  macOS: brew install tesseract-lang\n"
                    f"  Linux: sudo apt-get install tesseract-ocr-fra\n"
                    f"  Windows: Téléchargez fra.traineddata depuis https://github.com/tesseract-ocr/tessdata"
                )
            elif 'jpeg' in error_msg.lower() or 'corrupt' in error_msg.lower() or 'premature' in error_msg.lower() or 'bad data' in error_msg.lower():
                raise Exception(
                    f"L'image semble corrompue ou incomplète.\n"
                    f"💡 Suggestions:\n"
                    f"  • Réessayez de prendre la photo en vous assurant qu'elle est complète\n"
                    f"  • Vérifiez que le fichier n'a pas été interrompu lors de l'envoi\n"
                    f"  • Essayez de sauvegarder l'image depuis votre téléphone et ré-uploader\n"
                    f"  • Si l'image vient de WhatsApp, essayez de la sauvegarder d'abord puis de l'uploader\n"
                    f"  • Vérifiez que l'image n'est pas trop grande (essayez de la compresser si > 10MB)\n"
                    f"\nErreur technique: {error_msg[:200]}"
                )
            else:
                raise Exception(f"Erreur lors de l'extraction OCR: {error_msg}")
    
    def parse_transactions(self, text: str) -> List[Dict]:
        """
        Parse le texte extrait pour identifier les transactions
        Supporte plusieurs formats:
        - Format tableau bancaire: DD.MM | DD.MM | DESCRIPTION | DEBIT | CREDIT
        - Format simple: DATE | DESCRIPTION | MONTANT
        - Format libre avec dates et montants
        """
        transactions = []
        lines = text.split('\n')
        
        # Patterns pour détecter les transactions
        date_pattern_dot = r'(\d{1,2}\.\d{1,2})'  # Format DD.MM
        date_pattern_slash = r'(\d{1,2}[/-]\d{1,2}[/-]?\d{0,4})'  # Format DD/MM ou DD-MM
        amount_pattern = r'(\d{1,3}(?:\s?\d{3})*[.,]\d{2})'  # Montant avec espaces possibles (ex: 1 923,60)
        amount_pattern_simple = r'([+-]?\d+[.,]\d{2})'  # Montant simple
        
        current_year = datetime.now().year
        current_date = None
        
        # Détecter l'année depuis le texte si possible
        year_match = re.search(r'(\d{4})', text)
        if year_match:
            try:
                year = int(year_match.group(1))
                if 2020 <= year <= 2030:  # Année raisonnable
                    current_year = year
            except:
                pass
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Ignorer les lignes d'en-tête de tableau
            if line and line.lower():
                if any(keyword in line.lower() for keyword in ['date opé', 'date valeur', 'libellé', 'débit', 'crédit', 'total', 'solde']):
                    continue
            
            # Ignorer les lignes avec seulement des séparateurs
            if re.match(r'^[|\s\-]+$', line):
                continue
            
            # Format tableau bancaire: DD.MM | DD.MM | DESCRIPTION | DEBIT | CREDIT | ☐
            # Exemple: "10.10 | 10.10 | Virement Vir Inst vers walid lcl | 79,00 | | ☐"
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                # Essayer de parser comme un tableau
                date_op = None
                date_val = None
                description = None
                debit = None
                credit = None
                
                # Chercher les dates au début
                for i, part in enumerate(parts[:3]):
                    if re.match(date_pattern_dot, part):
                        if date_op is None:
                            date_op = part
                        elif date_val is None:
                            date_val = part
                    elif part and not re.match(r'^\d+\.\d+$', part):
                        # Si ce n'est pas une date, c'est probablement la description
                        if description is None and len(part) > 3:
                            description = part
                
                # Chercher les montants dans les colonnes suivantes
                for part in parts[3:]:
                    part_clean = part.replace(' ', '').replace('\xa0', '')
                    # Ignorer les cases vides et les symboles ☐
                    if not part_clean or part_clean in ['☐', '☑', '']:
                        continue
                    # Chercher un montant
                    amount_match = re.search(amount_pattern, part_clean)
                    if amount_match:
                        amount_str = amount_match.group(1).replace(' ', '').replace(',', '.')
                        try:
                            amount = float(amount_str)
                            if debit is None and amount > 0:
                                debit = amount
                            elif credit is None and amount > 0:
                                credit = amount
                        except ValueError:
                            pass
                
                # Si on a trouvé une description et un montant
                if description and (debit or credit):
                    amount = debit if debit else credit
                    # Utiliser date_op ou date_val pour la date
                    transaction_date = date_op or date_val or current_date
                    
                    if transaction_date and re.match(date_pattern_dot, transaction_date):
                        # Convertir DD.MM en format standard
                        day, month = transaction_date.split('.')
                        try:
                            formatted_date = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
                        except:
                            formatted_date = datetime.now().strftime('%Y-%m-%d')
                    else:
                        formatted_date = current_date if current_date else datetime.now().strftime('%Y-%m-%d')
                    
                    if amount > 0.01:  # Ignorer les montants trop petits
                        transactions.append({
                            'description': description.strip(),
                            'amount': abs(amount),
                            'date': formatted_date
                        })
                        continue
            
            # Format simple: chercher date et montant dans la ligne
            date_match = re.search(date_pattern_dot + r'|' + date_pattern_slash, line)
            if date_match and date_match.group(1):
                date_str = date_match.group(1)
                # Convertir DD.MM en format standard si nécessaire
                if date_str and '.' in date_str:
                    day, month = date_str.split('.')
                    try:
                        formatted_date = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
                        current_date = formatted_date
                    except:
                        current_date = date_str
                else:
                    current_date = date_str
            
            # Chercher un montant dans la ligne
            amount_match = re.search(amount_pattern, line)
            if not amount_match:
                amount_match = re.search(amount_pattern_simple, line)
            
            if amount_match:
                amount_str = amount_match.group(1).replace(' ', '').replace(',', '.')
                try:
                    amount = float(amount_str)
                    
                    # Extraire la description (tout sauf la date et le montant)
                    description = line
                    if date_match:
                        description = description.replace(date_match.group(0), '').strip()
                    description = description.replace(amount_match.group(0), '').strip()
                    description = re.sub(r'\s+', ' ', description)
                    
                    # Nettoyer la description
                    description = description.strip('|').strip('☐').strip('☑').strip()
                    
                    # Ignorer si la description est trop courte ou contient des mots-clés à ignorer
                    if not description or len(description) < 3:
                        continue
                    if any(keyword in description.lower() for keyword in ['total', 'solde', 'montant', 'débit', 'crédit']):
                        continue
                    
                    if description and abs(amount) > 0.01:
                        transaction_date = current_date if current_date else datetime.now().strftime('%Y-%m-%d')
                        transactions.append({
                            'description': description,
                            'amount': abs(amount),
                            'date': transaction_date
                        })
                except ValueError:
                    continue
        
        # Dédupliquer les transactions (parfois l'OCR peut créer des doublons)
        seen = set()
        unique_transactions = []
        for trans in transactions:
            key = (trans['description'][:50], trans['amount'], trans['date'])
            if key not in seen:
                seen.add(key)
                unique_transactions.append(trans)
        
        return unique_transactions

