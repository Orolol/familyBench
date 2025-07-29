"""Module pour construire les prompts d'évaluation."""

from typing import List, Dict, Any


class PromptBuilder:
    """Construit les prompts pour l'évaluation des modèles."""
    
    @staticmethod
    def build_single_question_prompt(tree_description: str, question: str, language: str = 'fr') -> str:
        """Construit le prompt pour une question unique."""
        if language == 'en':
            return f"""Here is a family description:

{tree_description}

Question: {question}

Respond ONLY with the requested name or list of names (separated by commas without spaces), or "None" if no one matches."""
        else:
            return f"""Voici la description d'une famille:

{tree_description}

Question: {question}

Réponds UNIQUEMENT avec le nom ou la liste de noms demandée (séparés par des virgules sans espaces), ou "Aucun" si personne ne correspond."""
    
    @staticmethod
    def build_batch_prompt(tree_description: str, questions: List[Dict[str, Any]], language: str = 'fr') -> str:
        """Construit le prompt pour un batch de questions."""
        questions_text = "\n".join([f"{i+1}. {q['question']}" for i, q in enumerate(questions)])
        
        if language == 'en':
            return f"""Here is a family description:

{tree_description}

Answer the following questions based on this family description. 
Provide your answers as a JSON array of strings in the same order as the questions.
For lists of names, separate them with commas without spaces.
If no one matches, answer "None".

Questions:
{questions_text}

Respond ONLY with a JSON array like: ["Answer1", "Answer2", "Answer3"]"""
        else:
            return f"""Voici la description d'une famille:

{tree_description}

Réponds aux questions suivantes basées sur cette description familiale.
Fournis tes réponses sous forme d'un tableau JSON de chaînes dans le même ordre que les questions.
Pour les listes de noms, sépare-les par des virgules sans espaces.
Si personne ne correspond, réponds "Aucun".

Questions:
{questions_text}

Réponds UNIQUEMENT avec un tableau JSON comme: ["Réponse1", "Réponse2", "Réponse3"]"""
    
    @staticmethod
    def get_system_prompt(language: str = 'fr', batch: bool = False) -> str:
        """Retourne le prompt système selon la langue et le mode."""
        if batch:
            return {
                "fr": "Tu es un assistant expert en analyse de texte. Réponds au format JSON demandé.",
                "en": "You are an expert text analysis assistant. Respond in the requested JSON format."
            }.get(language, "Tu es un assistant expert en analyse de texte. Réponds au format JSON demandé.")
        else:
            return {
                "fr": "Tu es un assistant expert en analyse de texte. Réponds UNIQUEMENT avec le nom ou la liste de noms demandée, sans aucune explication.",
                "en": "You are an expert text analysis assistant. Respond ONLY with the requested name or list of names, without any explanation."
            }.get(language, "Tu es un assistant expert en analyse de texte. Réponds UNIQUEMENT avec le nom ou la liste de noms demandée, sans aucune explication.")