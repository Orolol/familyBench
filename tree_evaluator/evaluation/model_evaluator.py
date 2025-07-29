"""Évaluateur principal pour les modèles via API."""

import asyncio
import json
import os
import re
import time
import logging
from typing import Dict, List, Any, Optional

import aiohttp

from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .result import EvaluationResult
from .answer_cleaner import AnswerCleaner
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Évaluateur pour un modèle via API OpenAI-compatible."""
    
    def __init__(self, config: Dict[str, Any]):
        self.name = config['name']
        self.api_base = config['api_base'].rstrip('/')
        self.api_key = self._resolve_api_key(config['api_key'])
        self.model = config['model']
        self.temperature = config.get('temperature', 0.0)
        self.max_tokens = config.get('max_tokens', 2000)
        self.language = 'fr'  # Will be set per benchmark
        self.reasoning_config = config.get('reasoning', None)
        self.cleaner = AnswerCleaner()
        self.prompt_builder = PromptBuilder()
        
    def _resolve_api_key(self, key: str) -> str:
        """Résout les variables d'environnement dans la clé API."""
        if key.startswith('${') and key.endswith('}'):
            env_var = key[2:-1]
            return os.environ.get(env_var, 'none')
        return key
    
    async def evaluate_question(self, 
                              tree_description: str,
                              question: Dict[str, Any],
                              session: aiohttp.ClientSession,
                              timeout: int = 60,
                              language: str = 'fr',
                              max_retries: int = 3) -> EvaluationResult:
        """Évalue une question unique avec retry automatique."""
        
        # Mesurer le temps de réponse total
        total_start_time = time.time()
        last_error = None
        
        # Retry loop
        for attempt in range(max_retries):
            if attempt > 0:
                # Attendre avant de réessayer (backoff exponentiel)
                wait_time = 2 ** attempt
                logger.info(f"Retry {attempt}/{max_retries} for {self.name} - Question {question['id']} after {wait_time}s wait")
                await asyncio.sleep(wait_time)
            
            try:
                result = await self._evaluate_question_single_attempt(
                    tree_description, question, session, timeout, language, total_start_time
                )
                
                # Si la réponse est valide ou si c'est la dernière tentative, retourner
                if not result.no_response or attempt == max_retries - 1:
                    if attempt > 0 and not result.no_response:
                        logger.info(f"Success after {attempt + 1} attempts for {self.name} - Question {question['id']}")
                    return result
                
                # Sinon, continuer avec la prochaine tentative
                logger.warning(f"Empty response on attempt {attempt + 1}/{max_retries} for {self.name} - Question {question['id']}")
                last_error = result
                
            except Exception as e:
                logger.error(f"Exception on attempt {attempt + 1}/{max_retries} for {self.name} - Question {question['id']}: {str(e)}")
                last_error = e
                if attempt == max_retries - 1:
                    return self._create_error_result(question, str(e), time.time() - total_start_time)
        
        # Si on arrive ici, toutes les tentatives ont échoué
        logger.error(f"All {max_retries} attempts failed for {self.name} - Question {question['id']}")
        if isinstance(last_error, EvaluationResult):
            return last_error
        return self._create_error_result(question, "All retry attempts failed", time.time() - total_start_time)
    
    async def _evaluate_question_single_attempt(self, 
                                               tree_description: str,
                                               question: Dict[str, Any],
                                               session: aiohttp.ClientSession,
                                               timeout: int,
                                               language: str,
                                               total_start_time: float) -> EvaluationResult:
        """Évalue une question unique - une seule tentative."""
        
        # Construire le prompt
        prompt = self.prompt_builder.build_single_question_prompt(
            tree_description, question['question'], language
        )
        
        # Mesurer le temps de réponse
        start_time = time.time()
        
        try:
            # Faire l'appel API
            headers = {
                "Content-Type": "application/json",
            }
            
            if self.api_key != "none":
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Adapter le format selon le type d'API
            data = self._build_api_request(prompt, language, batch=False)
            url = self._get_api_url()
            
            # Log de la requête envoyée
            logger.debug(f"Sending request to {url} for {self.name}")
            logger.debug(f"Request data: {json.dumps(data, indent=2)}")
            
            async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
                response_time = time.time() - start_time
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API Error {response.status} for {self.name}: {error_text}")
                    return self._create_error_result(
                        question, f"API Error {response.status}: {error_text}", response_time
                    )
                
                result = await response.json()
                
                # Log de debug pour les réponses API
                logger.debug(f"API Response for {self.name} - Question {question['id']}: {json.dumps(result, indent=2) if result else 'None'}")
                
                # Vérifier que result n'est pas None
                if result is None:
                    return self._create_error_result(
                        question, "Empty response from API", response_time, no_response=True
                    )
                
                # Extraire la réponse selon le format
                model_answer, tokens_used, reasoning_tokens, reasoning_text = self._extract_api_response(result)
                
                # Nettoyer la réponse
                model_answer = self.cleaner.clean_answer(model_answer, language)
                
                # Log si la réponse est vide ou très courte
                if not model_answer or len(model_answer) < 2:
                    logger.warning(f"Empty or very short answer from {self.name} for question {question['id']}: '{model_answer}'")
                    if reasoning_text:
                        logger.debug(f"Reasoning text was: {reasoning_text[:500]}...")
                
                # Détecter les non-réponses
                no_response = self.cleaner.is_no_response(model_answer)
                
                # Évaluer la réponse
                if no_response:
                    is_exact_match = False
                    partial_score = 0.0
                    is_correct = False
                else:
                    is_exact_match = self.cleaner.check_exact_match(model_answer, question['answer'])
                    partial_score = self.cleaner.calculate_partial_match(model_answer, question['answer'])
                    is_correct = is_exact_match or partial_score >= 0.9
                
                # Calculer le temps total depuis le début (incluant les retries)
                total_response_time = time.time() - total_start_time
                
                return EvaluationResult(
                    model_name=self.name,
                    benchmark_name="",
                    question_id=question['id'],
                    question=question['question'],
                    expected_answer=question['answer'],
                    model_answer=model_answer,
                    is_correct=is_correct,
                    is_exact_match=is_exact_match,
                    partial_match_score=partial_score,
                    response_time=total_response_time,
                    tokens_used=tokens_used,
                    no_response=no_response,
                    reasoning_tokens=reasoning_tokens,
                    reasoning_text=reasoning_text,
                    question_type=question.get('type'),
                    is_enigma=question.get('type') == 'enigme',
                    enigma_complexity=question.get('complexity') if question.get('type') == 'enigme' else None
                )
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout after {timeout}s for {self.name} on question {question['id']}")
            return self._create_error_result(question, "Timeout", time.time() - total_start_time)
        except Exception as e:
            logger.error(f"Exception for {self.name} on question {question['id']}: {str(e)}", exc_info=True)
            return self._create_error_result(question, str(e), time.time() - total_start_time)
    
    async def evaluate_questions_batch(self,
                                     tree_description: str,
                                     questions: List[Dict[str, Any]],
                                     session: aiohttp.ClientSession,
                                     timeout: int = 60,
                                     language: str = 'fr',
                                     max_retries: int = 3) -> List[EvaluationResult]:
        """Évalue un batch de questions en une seule requête avec retry automatique."""
        
        # Mesurer le temps de réponse total
        total_start_time = time.time()
        last_error = None
        
        # Retry loop
        for attempt in range(max_retries):
            if attempt > 0:
                # Attendre avant de réessayer (backoff exponentiel)
                wait_time = 2 ** attempt
                logger.info(f"Retry {attempt}/{max_retries} for {self.name} - Batch of {len(questions)} questions after {wait_time}s wait")
                await asyncio.sleep(wait_time)
            
            try:
                results = await self._evaluate_questions_batch_single_attempt(
                    tree_description, questions, session, timeout, language, total_start_time
                )
                
                # Vérifier si toutes les réponses sont vides
                all_empty = all(r.no_response for r in results)
                
                # Si au moins une réponse est valide ou si c'est la dernière tentative, retourner
                if not all_empty or attempt == max_retries - 1:
                    if attempt > 0 and not all_empty:
                        logger.info(f"Success after {attempt + 1} attempts for {self.name} - Batch of {len(questions)} questions")
                    return results
                
                # Sinon, continuer avec la prochaine tentative
                logger.warning(f"All responses empty on attempt {attempt + 1}/{max_retries} for {self.name} - Batch of {len(questions)} questions")
                last_error = results
                
            except Exception as e:
                logger.error(f"Exception on attempt {attempt + 1}/{max_retries} for {self.name} - Batch: {str(e)}")
                last_error = e
                if attempt == max_retries - 1:
                    # Retourner des erreurs pour toutes les questions
                    return [self._create_error_result(
                        q, str(e), (time.time() - total_start_time) / len(questions)
                    ) for q in questions]
        
        # Si on arrive ici, toutes les tentatives ont échoué
        logger.error(f"All {max_retries} attempts failed for {self.name} - Batch of {len(questions)} questions")
        if isinstance(last_error, list):
            return last_error
        # Retourner des erreurs pour toutes les questions
        return [self._create_error_result(
            q, "All retry attempts failed", (time.time() - total_start_time) / len(questions)
        ) for q in questions]
    
    async def _evaluate_questions_batch_single_attempt(self,
                                                     tree_description: str,
                                                     questions: List[Dict[str, Any]],
                                                     session: aiohttp.ClientSession,
                                                     timeout: int,
                                                     language: str,
                                                     total_start_time: float) -> List[EvaluationResult]:
        """Évalue un batch de questions en une seule requête - une seule tentative."""
        
        # Construire le prompt pour plusieurs questions
        prompt = self.prompt_builder.build_batch_prompt(tree_description, questions, language)
        
        # Mesurer le temps de réponse
        start_time = time.time()
        
        try:
            # Faire l'appel API
            headers = {
                "Content-Type": "application/json",
            }
            
            if self.api_key != "none":
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Adapter le format selon le type d'API
            data = self._build_api_request(prompt, language, batch=True)
            url = self._get_api_url()
            
            # Log de la requête envoyée
            logger.debug(f"Sending request to {url} for {self.name}")
            logger.debug(f"Request data: {json.dumps(data, indent=2)}")
            
            async with session.post(url, json=data, headers=headers, timeout=timeout) as response:
                response_time = time.time() - start_time
                
                if response.status != 200:
                    error_text = await response.text()
                    # Retourner des erreurs pour toutes les questions du batch
                    return [self._create_error_result(
                        q, f"API Error {response.status}: {error_text}", 
                        (time.time() - total_start_time) / len(questions)
                    ) for q in questions]
                
                result = await response.json()
                
                # Vérifier que result n'est pas None
                if result is None:
                    return [self._create_error_result(
                        q, "Empty response from API", response_time, no_response=True
                    ) for q in questions]
                
                # Extraire la réponse selon le format
                model_response, tokens_used, reasoning_tokens, reasoning_text = self._extract_api_response(result)
                
                # Parser la réponse JSON
                try:
                    # Extraire le JSON de la réponse
                    json_match = re.search(r'\[.*\]', model_response, re.DOTALL)
                    if json_match:
                        answers = json.loads(json_match.group())
                    else:
                        answers = json.loads(model_response)
                    
                    # S'assurer qu'on a le bon nombre de réponses
                    if len(answers) != len(questions):
                        answers = answers[:len(questions)] + [''] * (len(questions) - len(answers))
                    
                except:
                    # Si le parsing échoue, retourner des non-réponses
                    answers = [''] * len(questions)
                
                # Créer les résultats pour chaque question
                results = []
                for i, (question, answer) in enumerate(zip(questions, answers)):
                    # Nettoyer la réponse
                    model_answer = self.cleaner.clean_answer(str(answer), language)
                    
                    # Détecter les non-réponses
                    no_response = self.cleaner.is_no_response(model_answer)
                    
                    # Évaluer la réponse
                    if no_response:
                        is_exact_match = False
                        partial_score = 0.0
                        is_correct = False
                    else:
                        is_exact_match = self.cleaner.check_exact_match(model_answer, question['answer'])
                        partial_score = self.cleaner.calculate_partial_match(model_answer, question['answer'])
                        is_correct = is_exact_match or partial_score >= 0.9
                    
                    results.append(EvaluationResult(
                        model_name=self.name,
                        benchmark_name="",
                        question_id=question['id'],
                        question=question['question'],
                        expected_answer=question['answer'],
                        model_answer=model_answer,
                        is_correct=is_correct,
                        is_exact_match=is_exact_match,
                        partial_match_score=partial_score,
                        response_time=(time.time() - total_start_time) / len(questions),  # Temps moyen par question
                        tokens_used=tokens_used // len(questions),  # Tokens moyens par question
                        no_response=no_response,
                        reasoning_tokens=reasoning_tokens // len(questions) if reasoning_tokens > 0 else 0,
                        reasoning_text=reasoning_text,  # Partagé entre toutes les questions du batch
                        question_type=question.get('type'),
                        is_enigma=question.get('type') == 'enigme',
                        enigma_complexity=question.get('complexity') if question.get('type') == 'enigme' else None
                    ))
                
                return results
                
        except asyncio.TimeoutError:
            return [self._create_error_result(
                q, "Timeout", (time.time() - total_start_time) / len(questions)
            ) for q in questions]
            
        except Exception as e:
            return [self._create_error_result(
                q, str(e), (time.time() - total_start_time) / len(questions)
            ) for q in questions]
    
    def _build_api_request(self, prompt: str, language: str, batch: bool = False) -> Dict[str, Any]:
        """Construit la requête API selon le type d'API."""
        if "anthropic" in self.api_base:
            # Format Anthropic
            return {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        else:
            # Format OpenAI
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt_builder.get_system_prompt(language, batch)},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            # Ajouter la configuration de reasoning si présente
            if self.reasoning_config and "openrouter" in self.api_base:
                data["reasoning"] = self.reasoning_config
            
            return data
    
    def _get_api_url(self) -> str:
        """Retourne l'URL de l'API selon le type."""
        if "anthropic" in self.api_base:
            return f"{self.api_base}/messages"
        else:
            return f"{self.api_base}/chat/completions"
    
    def _extract_api_response(self, result: Dict[str, Any]) -> tuple[str, int, int, Optional[str]]:
        """Extrait la réponse du modèle selon le format de l'API."""
        reasoning_tokens = 0
        reasoning_text = None
        
        if "anthropic" in self.api_base:
            content = result.get('content', [{}])
            if content and len(content) > 0:
                model_answer = content[0].get('text') or ''
            else:
                model_answer = ''
            model_answer = model_answer.strip()
            tokens_used = result.get('usage', {}).get('output_tokens', 0)
        else:
            choices = result.get('choices', [])
            if not choices:
                logger.warning(f"No choices in API response for {self.name} - Full response: {json.dumps(result, indent=2)}")
                return "", 0, 0, None
            
            choice = choices[0]
            message = choice.get('message', {})
            model_answer = message.get('content') or ''
            
            # Log de debug si la réponse est vide
            if not model_answer:
                logger.warning(f"Empty content in message for {self.name} - Message: {json.dumps(message, indent=2)}")
            
            model_answer = model_answer.strip()
            tokens_used = result.get('usage', {}).get('completion_tokens', 0)
            
            # Extraire les tokens de reasoning si présents (OpenRouter)
            if 'reasoning' in message:
                reasoning_text = message['reasoning']
                # Les tokens de reasoning sont comptabilisés dans le total
                # On peut estimer en fonction de la longueur du texte
                if reasoning_text:
                    reasoning_tokens = len(reasoning_text.split()) * 2  # Estimation approximative
                    logger.debug(f"Found reasoning text ({len(reasoning_text)} chars) for {self.name}")
            
            # Vérifier si le contenu est dans un format différent pour les modèles de reasoning
            if not model_answer and 'reasoning_content' in message:
                model_answer = message.get('reasoning_content', '')
                logger.debug(f"Using reasoning_content as answer for {self.name}")
            
            # Vérifier aussi dans usage pour les tokens de reasoning
            usage = result.get('usage', {})
            if 'reasoning_tokens' in usage:
                reasoning_tokens = usage['reasoning_tokens']
        
        return model_answer, tokens_used, reasoning_tokens, reasoning_text
    
    def _create_error_result(self, question: Dict[str, Any], error: str, response_time: float, no_response: bool = False) -> EvaluationResult:
        """Crée un résultat d'erreur."""
        return EvaluationResult(
            model_name=self.name,
            benchmark_name="",
            question_id=question['id'],
            question=question['question'],
            expected_answer=question['answer'],
            model_answer="",
            is_correct=False,
            is_exact_match=False,
            partial_match_score=0.0,
            response_time=response_time,
            tokens_used=0,
            error=error,
            no_response=no_response,
            reasoning_tokens=0,
            reasoning_text=None,
            question_type=question.get('type'),
            is_enigma=question.get('type') == 'enigme',
            enigma_complexity=question.get('complexity') if question.get('type') == 'enigme' else None
        )