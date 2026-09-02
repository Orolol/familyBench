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

Please think carefully, as the quality of your response is of the highest priority. You have unlimited thinking tokens for this. Reasoning: high

Response format:
- If the question asks "how many" or "combien", respond with a single NUMBER (e.g. 3), not names.
- If the question asks for people/names, respond with FIRST NAMES only, separated by commas without spaces (e.g. Alice,Bob,Claire).
- If no one matches, respond "None".
- Do NOT add any explanation, just the answer."""
        else:
            return f"""Voici la description d'une famille:

{tree_description}

Question: {question}

Please think carefully, as the quality of your response is of the highest priority. You have unlimited thinking tokens for this. Reasoning: high

Format de réponse :
- Si la question demande "combien" ou un dénombrement, réponds avec un CHIFFRE uniquement (ex: 3), pas des noms.
- Si la question demande des personnes/noms, réponds avec les PRÉNOMS uniquement, séparés par des virgules sans espaces (ex: Alice,Bob,Claire).
- Si personne ne correspond, réponds "Aucun".
- N'ajoute AUCUNE explication, juste la réponse."""
    
    @staticmethod
    def build_batch_prompt(tree_description: str, questions: List[Dict[str, Any]], language: str = 'fr') -> str:
        """Construit le prompt pour un batch de questions.

        Les réponses sont demandées sous forme d'objet JSON indexé par numéro
        de question ({"1": ..., "2": ...}) : contrairement à un tableau, une
        question sautée ne décale pas toutes les suivantes.
        """
        questions_text = "\n".join([f"{i+1}. {q['question']}" for i, q in enumerate(questions)])
        n = len(questions)
        example = ", ".join(f'"{i}": "..."' for i in range(1, min(n, 3) + 1))
        if n > 3:
            example += f', ..., "{n}": "..."'

        if language == 'en':
            return f"""Here is a family description:

{tree_description}

Answer the following {n} questions based on this family description.

Questions:
{questions_text}

Please think carefully, as the quality of your response is of the highest priority. You have unlimited thinking tokens for this. Reasoning: high

Response format:
- If a question asks "how many", answer with a single NUMBER (e.g. "3"), not names.
- If a question asks for people/names, answer with FIRST NAMES only, separated by commas without spaces (e.g. "Alice,Bob,Claire").
- If no one matches, answer "None".
- Answer every question, using its number as the key.
- Respond ONLY with one JSON object like: {{{example}}} and no other text."""
        else:
            return f"""Voici la description d'une famille:

{tree_description}

Réponds aux {n} questions suivantes en te basant sur cette description familiale.

Questions:
{questions_text}

Please think carefully, as the quality of your response is of the highest priority. You have unlimited thinking tokens for this. Reasoning: high

Format de réponse :
- Si une question demande "combien" ou un dénombrement, réponds avec un CHIFFRE uniquement (ex: "3"), pas des noms.
- Si une question demande des personnes/noms, réponds avec les PRÉNOMS uniquement, séparés par des virgules sans espaces (ex: "Alice,Bob,Claire").
- Si personne ne correspond, réponds "Aucun".
- Réponds à toutes les questions, en utilisant leur numéro comme clé.
- Réponds UNIQUEMENT avec un objet JSON comme: {{{example}}} et rien d'autre."""

    @staticmethod
    def get_system_prompt(language: str = 'fr', batch: bool = False) -> str:
        """Retourne le prompt système selon la langue et le mode."""
        if batch:
            return {
                "fr": "Tu es un assistant expert en analyse de texte. Réponds au format JSON demandé. Pour les questions de dénombrement, réponds par un chiffre. Pour les questions de noms, réponds par des prénoms.",
                "en": "You are an expert text analysis assistant. Respond in the requested JSON format. For counting questions, answer with a number. For name questions, answer with first names."
            }.get(language, "Tu es un assistant expert en analyse de texte. Réponds au format JSON demandé.")
        else:
            return {
                "fr": "Tu es un assistant expert en analyse de texte. Pour les questions de dénombrement, réponds par un chiffre uniquement. Pour les questions de noms, réponds par des prénoms uniquement, sans explication.",
                "en": "You are an expert text analysis assistant. For counting questions, respond with a number only. For name questions, respond with first names only, without any explanation."
            }.get(language, "Tu es un assistant expert en analyse de texte. Réponds UNIQUEMENT avec la réponse demandée, sans aucune explication.")