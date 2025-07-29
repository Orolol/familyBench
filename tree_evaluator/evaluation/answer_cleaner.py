"""Module pour nettoyer et normaliser les réponses des modèles."""

import re
import logging

logger = logging.getLogger(__name__)


class AnswerCleaner:
    """Nettoie et normalise les réponses des modèles."""
    
    @staticmethod
    def clean_answer(answer: str, language: str = 'fr') -> str:
        """Nettoie la réponse du modèle."""
        # Log de la réponse originale pour debug
        if '|begin_of_box|>' in answer or '<answer>' in answer:
            logger.debug(f"Original answer before cleaning: {answer}")
        
        # Gérer le format GLM avec |begin_of_box|>...<|end_of_box|>
        glm_match = re.search(r'\|begin_of_box\|>(.*?)<\|end_of_box\|>', answer, re.DOTALL)
        if glm_match:
            answer = glm_match.group(1).strip()
            logger.debug(f"Extracted from GLM box format: {answer}")
        
        # D'abord chercher si la réponse contient un tag <answer>
        answer_match = re.search(r'<answer>(.*?)(?:</answer>|$)', answer, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()
        
        # Chercher d'autres formats courants comme **Answer:** ou Answer:
        if not glm_match and not answer_match:
            # Format **Answer:** ou Answer:
            answer_pattern = re.search(r'(?:\*\*)?Answer\s*:\s*(.+?)(?:\n|$)', answer, re.IGNORECASE)
            if answer_pattern:
                answer = answer_pattern.group(1).strip()
            
            # Format The answer is: ... ou La réponse est: ...
            answer_is_pattern = re.search(r'(?:The answer is|La réponse est)\s*:?\s*(.+?)(?:\n|$)', answer, re.IGNORECASE)
            if answer_is_pattern:
                answer = answer_is_pattern.group(1).strip()
            
            # Format [Answer] ou [[Answer]]
            bracket_match = re.search(r'\[+([^\[\]]+)\]+', answer)
            if bracket_match and len(bracket_match.group(1)) < 100:  # Éviter les faux positifs
                answer = bracket_match.group(1).strip()
            
            # Format {Answer} ou {{Answer}}
            brace_match = re.search(r'\{+([^\{\}]+)\}+', answer)
            if brace_match and len(brace_match.group(1)) < 100:
                answer = brace_match.group(1).strip()
            
            # Format <|Answer|> ou variations
            pipe_match = re.search(r'<\|([^|]+)\|>', answer)
            if pipe_match:
                answer = pipe_match.group(1).strip()
            
            # Format Final answer: ... ou Réponse finale: ...
            final_answer_pattern = re.search(r'(?:Final answer|Réponse finale)\s*:?\s*(.+?)(?:\n|$)', answer, re.IGNORECASE)
            if final_answer_pattern:
                answer = final_answer_pattern.group(1).strip()
        
        # Enlever les guillemets, points, espaces superflus
        answer = answer.strip()
        answer = answer.strip('"\'')
        answer = answer.rstrip('.')
        
        # Si la réponse contient une explication après deux-points, essayer d'extraire juste les noms
        if ':' in answer and not any(char in answer.split(':')[0] for char in [',', ' ']):
            # Ne pas split si c'est déjà une liste de noms
            potential_answer = answer.split(':')[-1].strip()
            # Vérifier que ce n'est pas une explication longue
            if len(potential_answer) < len(answer) * 0.8:
                answer = potential_answer
        
        # Gérer différents formats de listes
        # Remplacer "and" ou "et" par des virgules
        answer = re.sub(r'\s+(?:and|et)\s+', ',', answer, flags=re.IGNORECASE)
        
        # Remplacer les points-virgules ou barres verticales par des virgules
        answer = answer.replace(';', ',').replace('|', ',')
        
        # Normaliser les virgules (enlever les espaces autour)
        answer = re.sub(r'\s*,\s*', ',', answer)
        
        # Enlever les virgules en début ou fin
        answer = answer.strip(',')
        
        # Normaliser "None" en "Aucun" pour le français si nécessaire
        if language == 'fr' and answer.lower() == 'none':
            answer = 'Aucun'
        elif language == 'en' and answer.lower() == 'aucun':
            answer = 'None'
        
        # Gérer les variations de "None" ou "Aucun"
        if answer.lower() in ['no one', 'nobody', 'personne', 'aucune personne', 'null', 'nil', 'n/a']:
            if language == 'fr':
                answer = 'Aucun'
            else:
                answer = 'None'
        
        # Pour les réponses numériques, extraire juste le nombre
        # Utile pour les questions de comptage
        if re.match(r'^(?:The answer is|La réponse est|Answer|Réponse)\s*:?\s*(\d+)', answer, re.IGNORECASE):
            number_match = re.search(r'\d+', answer)
            if number_match:
                answer = number_match.group()
        
        # Gérer les nombres écrits en toutes lettres (pour les petits nombres)
        number_words = {
            'zero': '0', 'zéro': '0',
            'one': '1', 'un': '1', 'une': '1',
            'two': '2', 'deux': '2',
            'three': '3', 'trois': '3',
            'four': '4', 'quatre': '4',
            'five': '5', 'cinq': '5',
            'six': '6', 'six': '6',
            'seven': '7', 'sept': '7',
            'eight': '8', 'huit': '8',
            'nine': '9', 'neuf': '9',
            'ten': '10', 'dix': '10'
        }
        
        answer_lower = answer.lower()
        if answer_lower in number_words:
            answer = number_words[answer_lower]
        
        # Log du résultat final si on a fait une extraction
        if glm_match or answer_match:
            logger.debug(f"Final cleaned answer: {answer}")
        
        return answer
    
    @staticmethod
    def is_no_response(answer: str) -> bool:
        """Détecte si le modèle n'a pas répondu à la question."""
        # Log pour debug si la réponse est très courte
        if answer and len(answer) < 2:
            logger.debug(f"Checking if very short answer '{answer}' is a no-response")
        
        # Patterns indiquant une non-réponse
        no_response_patterns = [
            # Réponses vides ou presque vides
            '',
            '.',
            '...',
            '-',
            '_',
            'n/a',
            'na',
            # Réponses indiquant l'incapacité
            "i don't know",
            "i do not know",
            "je ne sais pas",
            "je ne peux pas",
            "cannot answer",
            "unable to answer",
            "no information",
            "not enough information",
            "impossible to answer",
            "impossible de répondre",
            # Réponses génériques
            "the answer",
            "la réponse",
            "answer:",
            "réponse:",
        ]
        
        # Vérifier si la réponse correspond à un pattern de non-réponse
        answer_lower = answer.lower().strip()
        
        # Vérification exacte
        if answer_lower in no_response_patterns:
            return True
        
        # Vérification si la réponse contient uniquement des caractères non alphabétiques
        if not any(c.isalpha() for c in answer):
            return True
        
        # Vérification si la réponse est trop courte et ne contient pas de nom propre
        if len(answer_lower) < 3 and not answer[0].isupper():
            return True
        
        # Vérifier si c'est une phrase complète au lieu d'une réponse
        if any(phrase in answer_lower for phrase in [
            "i cannot", "je ne peux", "there is no", "il n'y a pas",
            "based on the", "selon le", "the text", "le texte"
        ]):
            return True
        
        return False
    
    @staticmethod
    def check_exact_match(model_answer: str, expected_answer: str) -> bool:
        """Vérifie si la réponse correspond exactement."""
        # Normaliser les deux réponses
        model_normalized = set(model_answer.split(',')) if ',' in model_answer else {model_answer}
        expected_normalized = set(expected_answer.split(',')) if ',' in expected_answer else {expected_answer}
        
        return model_normalized == expected_normalized
    
    @staticmethod
    def calculate_partial_match(model_answer: str, expected_answer: str) -> float:
        """Calcule un score de correspondance partielle."""
        if model_answer == expected_answer:
            return 1.0
        
        # Pour les listes
        if ',' in expected_answer or ',' in model_answer:
            model_set = set(model_answer.split(',')) if model_answer else set()
            expected_set = set(expected_answer.split(',')) if expected_answer else set()
            
            if not expected_set:
                return 0.0
            
            # Score basé sur l'intersection
            intersection = model_set & expected_set
            union = model_set | expected_set
            
            if not union:
                return 0.0
            
            return len(intersection) / len(union)
        
        # Pour les réponses simples
        return 1.0 if model_answer.lower() == expected_answer.lower() else 0.0