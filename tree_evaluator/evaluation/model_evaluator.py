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
from ..cache_manager import CacheManager

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Évaluateur pour un modèle via API OpenAI-compatible."""

    # Une réponse est comptée correcte si elle est un match exact (mêmes noms,
    # ordre ignoré) OU si son score de Jaccard avec la réponse attendue est
    # >= ce seuil. Sur des listes courtes cela revient à exiger l'exact match ;
    # sur des listes longues (>= 10 noms) cela tolère un nom manquant/en trop.
    CORRECT_PARTIAL_THRESHOLD = 0.9

    def __init__(self, config: Dict[str, Any]):
        self.name = config['name']
        self.api_base = config['api_base'].rstrip('/')
        self.api_key = self._resolve_api_key(config['api_key'])
        self.model = config['model']
        self.temperature = config.get('temperature', 0.8)
        self.max_tokens = config.get('max_tokens', 64000)
        self.max_completion_tokens = config.get('max_completion_tokens')
        self.language = 'fr'  # Will be set per benchmark
        self.reasoning_config = config.get('reasoning', None)
        self.provider_config = config.get('provider', None)
        self.request_delay_ms = config.get('request_delay_ms', 0)  # Delay between requests in milliseconds
        # Pricing (USD per million tokens). Optional; absent => no cost computed.
        # Expected keys: input_per_mtok, output_per_mtok, cached_input_per_mtok (optional).
        self.pricing: Optional[Dict[str, float]] = config.get('pricing')
        self.cleaner = AnswerCleaner()
        self.prompt_builder = PromptBuilder()
        self.cache_manager = CacheManager()
        # Prénoms présents dans l'arbre courant (défini par le runner) pour
        # détecter les noms inventés dans les réponses.
        self.known_names: set = set()

    def set_known_names(self, names) -> None:
        """Définit les prénoms valides de l'arbre en cours d'évaluation."""
        self.known_names = set(names)

    _NONE_TOKENS = ('none', 'aucun', 'aucune')

    def _is_name_list(self, answer: str, known_lower: set) -> bool:
        """True si `answer` est une liste (non vide) de prénoms de l'arbre."""
        tokens = [t.strip() for t in answer.split(',') if t.strip()]
        return bool(tokens) and all(t.lower() in known_lower for t in tokens)

    def count_hallucinated_names(self, model_answer: str, expected_answer: str = "") -> int:
        """Nombre de prénoms de la réponse qui n'existent pas dans l'arbre.

        Ne s'applique que si la réponse attendue est elle-même une liste de
        prénoms : les questions dont la réponse est un nombre, "None"/"Aucun",
        un attribut (couleur...) ou un libellé de relation renvoient 0.
        """
        if not self.known_names or not model_answer:
            return 0
        known_lower = {n.lower() for n in self.known_names}
        if expected_answer and not self._is_name_list(expected_answer, known_lower):
            return 0
        if model_answer.strip().isdigit():
            return 0
        count = 0
        for token in model_answer.split(','):
            token = token.strip()
            if not token or token.lower() in self._NONE_TOKENS:
                continue
            if token.lower() not in known_lower:
                count += 1
        return count

    def _compute_cost(
        self, prompt_tokens: int, completion_tokens: int, cached_tokens: int
    ) -> Optional[float]:
        """Cost in USD given the pricing dict, or None if no pricing set."""
        if not self.pricing:
            return None
        in_rate = float(self.pricing.get('input_per_mtok', 0.0) or 0.0)
        out_rate = float(self.pricing.get('output_per_mtok', 0.0) or 0.0)
        cached_rate_raw = self.pricing.get('cached_input_per_mtok')
        cached_rate = float(cached_rate_raw) if cached_rate_raw is not None else in_rate
        non_cached_in = max(0, prompt_tokens - cached_tokens)
        return (
            non_cached_in * in_rate
            + cached_tokens * cached_rate
            + completion_tokens * out_rate
        ) / 1_000_000
        
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
            
            # Vérifier le cache
            cache_key = {
                "model": self.name,
                "url": url,
                "data": data
            }
            cached_response = self.cache_manager.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {self.name} - Question {question['id']}")
                result = cached_response
                # Simuler un temps de réponse nul ou très court pour le cache
                response_time = 0.001
            else:
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
                    
                    # Sauvegarder dans le cache si succès
                    if result:
                        self.cache_manager.set(cache_key, result)
                
            # Log de debug pour les réponses API
            logger.debug(f"API Response for {self.name} - Question {question['id']}: {json.dumps(result, indent=2) if result else 'None'}")
            
            # Vérifier que result n'est pas None
            if result is None:
                return self._create_error_result(
                    question, "Empty response from API", response_time, no_response=True
                )
            
            # Extraire la réponse selon le format
            (
                model_answer,
                tokens_used,
                reasoning_tokens,
                reasoning_text,
                prompt_tokens,
                cached_tokens,
            ) = self._extract_api_response(result)

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
                is_correct = is_exact_match or partial_score >= self.CORRECT_PARTIAL_THRESHOLD
            
            # Calculer le temps total depuis le début (incluant les retries)
            total_response_time = time.time() - total_start_time
            
            return EvaluationResult(
                model_name=self.name,
                benchmark_name="",
                question_id=question['id'],
                question=question['question'],
                expected_answer=question['answer'],
                model_answer=model_answer,
                hallucinated_names=self.count_hallucinated_names(model_answer, question['answer']),
                is_correct=is_correct,
                is_exact_match=is_exact_match,
                partial_match_score=partial_score,
                response_time=total_response_time,
                tokens_used=tokens_used,
                no_response=no_response,
                reasoning_tokens=reasoning_tokens,
                reasoning_text=reasoning_text,
                prompt_tokens=prompt_tokens,
                cached_tokens=cached_tokens,
                cost_usd=self._compute_cost(prompt_tokens, tokens_used, cached_tokens),
                question_type=question.get('type'),
                difficulty=question.get('difficulty'),
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
            
            # Vérifier le cache
            cache_key = {
                "model": self.name,
                "url": url,
                "data": data
            }
            cached_response = self.cache_manager.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {self.name} - Batch of {len(questions)} questions")
                result = cached_response
                response_time = 0.001
            else:
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
                    
                    # Sauvegarder dans le cache si succès
                    if result:
                        self.cache_manager.set(cache_key, result)
                
            # Vérifier que result n'est pas None
            if result is None:
                return [self._create_error_result(
                    q, "Empty response from API", response_time, no_response=True
                ) for q in questions]
            
            # Extraire la réponse selon le format
            (
                model_response,
                tokens_used,
                reasoning_tokens,
                reasoning_text,
                prompt_tokens,
                cached_tokens,
            ) = self._extract_api_response(result)

            # Parser la réponse (objet JSON indexé, tableau JSON ou liste numérotée)
            answers = self.parse_batch_answers(model_response, len(questions))
            if not any(answers):
                logger.warning(f"Could not parse any answer from batch response for {self.name}: {model_response[:300]!r}")
            
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
                    is_correct = is_exact_match or partial_score >= self.CORRECT_PARTIAL_THRESHOLD
                
                per_q_prompt = prompt_tokens // len(questions)
                per_q_completion = tokens_used // len(questions)
                per_q_cached = cached_tokens // len(questions)
                results.append(EvaluationResult(
                    model_name=self.name,
                    benchmark_name="",
                    question_id=question['id'],
                    question=question['question'],
                    expected_answer=question['answer'],
                    model_answer=model_answer,
                    hallucinated_names=self.count_hallucinated_names(model_answer, question['answer']),
                    is_correct=is_correct,
                    is_exact_match=is_exact_match,
                    partial_match_score=partial_score,
                    response_time=(time.time() - total_start_time) / len(questions),  # Temps moyen par question
                    tokens_used=per_q_completion,
                    no_response=no_response,
                    reasoning_tokens=reasoning_tokens // len(questions) if reasoning_tokens > 0 else 0,
                    reasoning_text=reasoning_text,  # Partagé entre toutes les questions du batch
                    prompt_tokens=per_q_prompt,
                    cached_tokens=per_q_cached,
                    cost_usd=self._compute_cost(per_q_prompt, per_q_completion, per_q_cached),
                    question_type=question.get('type'),
                    difficulty=question.get('difficulty'),
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
    
    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(str(v).strip() for v in value if str(v).strip())
        return str(value).strip()

    @classmethod
    def parse_batch_answers(cls, text: str, n: int) -> List[str]:
        """Extrait `n` réponses d'une réponse batch.

        Stratégies, dans l'ordre :
        1. le dernier objet JSON de la réponse, indexé par numéro de question
           ({"1": "Alice", "2": "3"}) : les clés absentes donnent "" ;
        2. le dernier tableau JSON (positionnel) ;
        3. des lignes numérotées ("1. Alice", "2) 3").
        Les réponses manquantes sont renvoyées comme chaînes vides.
        """
        answers = [""] * n
        if not text:
            return answers
        # Retirer les blocs de raisonnement / fences markdown éventuels
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        cleaned = cleaned.replace("```json", "```")

        # 1 & 2 : tout JSON valide commençant à un '{' ou '[' (raw_decode gère
        # l'imbrication). Priorité : le dernier objet indexé par numéro, sinon
        # le tableau le plus long (le tableau externe, pas une sous-liste).
        decoder = json.JSONDecoder()
        best_dict = None
        best_list = None  # (span, parsed)
        for pos in range(len(cleaned) - 1, -1, -1):
            if cleaned[pos] not in "{[":
                continue
            try:
                parsed, consumed = decoder.raw_decode(cleaned[pos:])
            except ValueError:
                continue
            if isinstance(parsed, dict) and best_dict is None:
                if any(re.search(r"\d+", str(k)) for k in parsed):
                    best_dict = parsed
                    break  # le dernier objet numéroté gagne
            elif isinstance(parsed, list) and parsed:
                if best_list is None or consumed > best_list[0]:
                    best_list = (consumed, parsed)
        if best_dict is not None:
            for key, value in best_dict.items():
                m = re.search(r"\d+", str(key))
                if not m:
                    continue
                idx = int(m.group()) - 1
                if 0 <= idx < n:
                    answers[idx] = cls._to_text(value)
            return answers
        if best_list is not None:
            for idx, value in enumerate(best_list[1][:n]):
                answers[idx] = cls._to_text(value)
            return answers

        # 3 : lignes numérotées
        for m in re.finditer(r"^\s*\**(\d{1,3})\**\s*[.):\-]\s*(.+?)\s*$", cleaned, re.MULTILINE):
            idx = int(m.group(1)) - 1
            if 0 <= idx < n:
                answers[idx] = m.group(2).strip().strip('"\'')
        return answers

    def _build_api_request(self, prompt: str, language: str, batch: bool = False) -> Dict[str, Any]:
        """Construit la requête API selon le type d'API."""
        if "anthropic" in self.api_base:
            # Format Anthropic
            return {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_completion_tokens": self.max_completion_tokens if self.max_completion_tokens is not None else (self.max_tokens if self.max_tokens is not None else 2000)
            }
        elif self.reasoning_config and "openai" in self.api_base:
            # Format OpenAI Responses API (pour les modèles avec reasoning comme gpt-5.1)
            data = {
                "model": self.model,
                "input": [
                    {"role": "system", "content": self.prompt_builder.get_system_prompt(language, batch)},
                    {"role": "user", "content": prompt}
                ],
                # Note: temperature might not be supported or works differently in Responses API, 
                # but keeping it if not explicitly forbidden.
                # "temperature": self.temperature, 
            }
            
            if self.reasoning_config:
                data["reasoning"] = self.reasoning_config
                
            # Responses API uses max_output_tokens
            if self.max_completion_tokens:
                data["max_output_tokens"] = self.max_completion_tokens
            elif self.max_tokens:
                 data["max_output_tokens"] = self.max_tokens
                
            return data
        else:
            # Format OpenAI Standard
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt_builder.get_system_prompt(language, batch)},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
            }
            
            if self.max_completion_tokens:
                data["max_completion_tokens"] = self.max_completion_tokens
            else:
                data["max_tokens"] = self.max_tokens if self.max_tokens is not None else 2000
            
            # Ajouter la configuration de reasoning si présente (pour OpenRouter etc)
            if self.reasoning_config and "openrouter" in self.api_base:
                data["reasoning"] = self.reasoning_config

            if self.provider_config and "openrouter" in self.api_base:
                data["provider"] = self.provider_config

            return data
    
    def _get_api_url(self) -> str:
        """Retourne l'URL de l'API selon le type."""
        if "anthropic" in self.api_base:
            return f"{self.api_base}/messages"
        elif self.reasoning_config and "openai" in self.api_base:
            return f"{self.api_base}/responses"
        else:
            return f"{self.api_base}/chat/completions"
    
    def _extract_api_response(
        self, result: Dict[str, Any]
    ) -> tuple[str, int, int, Optional[str], int, int]:
        """Extrait la réponse du modèle selon le format de l'API.

        Returns: (model_answer, completion_tokens, reasoning_tokens,
                  reasoning_text, prompt_tokens, cached_tokens)

        Tolère les deux schémas d'usage:
          • OpenAI / vLLM: prompt_tokens, completion_tokens,
            prompt_tokens_details.cached_tokens
          • Anthropic / OpenRouter récent: input_tokens, output_tokens,
            input_tokens_details.cached_tokens
        """
        reasoning_tokens = 0
        reasoning_text = None
        prompt_tokens = 0
        cached_tokens = 0

        # Format Responses API (OpenAI, /responses) : la réponse est dans
        # result["output"] = [{type: "reasoning"...}, {type: "message", content: [{type: "output_text", text}]}]
        if "output" in result and "choices" not in result:
            text_parts = []
            for item in result.get("output") or []:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                for part in item.get("content") or []:
                    if isinstance(part, dict) and part.get("type") == "output_text":
                        text_parts.append(part.get("text") or "")
            model_answer = (result.get("output_text") or "\n".join(text_parts)).strip()
            usage = result.get("usage", {}) or {}
            tokens_used = int(usage.get("output_tokens", 0) or 0)
            prompt_tokens = int(usage.get("input_tokens", 0) or 0)
            in_details = usage.get("input_tokens_details") or {}
            out_details = usage.get("output_tokens_details") or {}
            cached_tokens = int(in_details.get("cached_tokens", 0) or 0)
            reasoning_tokens = int(out_details.get("reasoning_tokens", 0) or 0)
            if not model_answer:
                logger.warning(f"Empty output in Responses API result for {self.name} - Full response: {json.dumps(result, indent=2)}")
            return model_answer, tokens_used, reasoning_tokens, reasoning_text, prompt_tokens, cached_tokens

        if "anthropic" in self.api_base:
            content = result.get('content', [{}])
            if content and len(content) > 0:
                model_answer = content[0].get('text') or ''
            else:
                model_answer = ''
            model_answer = model_answer.strip()
            usage = result.get('usage', {}) or {}
            tokens_used = usage.get('output_tokens', 0)
            prompt_tokens = usage.get('input_tokens', 0)
            in_details = usage.get('input_tokens_details') or {}
            cached_tokens = int(in_details.get('cached_tokens', 0) or 0)
        else:
            choices = result.get('choices', [])
            if not choices:
                logger.warning(f"No choices in API response for {self.name} - Full response: {json.dumps(result, indent=2)}")
                return "", 0, 0, None, 0, 0

            choice = choices[0]
            message = choice.get('message', {})
            content = message.get('content') or ''

            # Handle both string and list content formats
            if isinstance(content, list):
                # Extract text from list format (e.g., with thinking/text blocks)
                text_parts = []
                thinking_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text' and 'text' in item:
                            text_parts.append(item['text'])
                        elif item.get('type') == 'thinking' and 'thinking' in item:
                            # Extract reasoning text for models with thinking blocks
                            thinking_data = item['thinking']
                            if isinstance(thinking_data, list):
                                for think_item in thinking_data:
                                    if isinstance(think_item, dict) and 'text' in think_item:
                                        thinking_parts.append(think_item['text'])
                        elif 'text' in item:  # fallback for other structures
                            text_parts.append(item['text'])
                model_answer = ' '.join(text_parts)
                if thinking_parts:
                    reasoning_text = ' '.join(thinking_parts)
                    reasoning_tokens = len(reasoning_text.split()) * 2  # Rough estimation
                    logger.debug(f"Extracted reasoning from thinking blocks for {self.name} ({len(reasoning_text)} chars)")
            else:
                model_answer = content

            # Log de debug si la réponse est vide
            if not model_answer:
                logger.warning(f"Empty content in message for {self.name} - Message: {json.dumps(message, indent=2)}")

            model_answer = model_answer.strip()
            usage = result.get('usage', {}) or {}
            tokens_used = usage.get('completion_tokens', usage.get('output_tokens', 0))
            prompt_tokens = usage.get('prompt_tokens', usage.get('input_tokens', 0))
            in_details = (
                usage.get('prompt_tokens_details') or usage.get('input_tokens_details') or {}
            )
            out_details = (
                usage.get('completion_tokens_details')
                or usage.get('output_tokens_details')
                or {}
            )
            cached_tokens = int((in_details or {}).get('cached_tokens', 0) or 0)
            reasoning_from_details = int((out_details or {}).get('reasoning_tokens', 0) or 0)
            if reasoning_from_details:
                reasoning_tokens = reasoning_from_details

            # Extraire les tokens de reasoning si présents (OpenRouter)
            if 'reasoning' in message:
                reasoning_text = message['reasoning']
                # Les tokens de reasoning sont comptabilisés dans le total
                # On peut estimer en fonction de la longueur du texte
                if reasoning_text and not reasoning_tokens:
                    reasoning_tokens = len(reasoning_text.split()) * 2  # Estimation approximative
                    logger.debug(f"Found reasoning text ({len(reasoning_text)} chars) for {self.name}")

            # Vérifier si le contenu est dans un format différent pour les modèles de reasoning
            if not model_answer and 'reasoning_content' in message:
                model_answer = message.get('reasoning_content', '')
                logger.debug(f"Using reasoning_content as answer for {self.name}")

            # Vérifier aussi dans usage pour les tokens de reasoning (champ legacy)
            if not reasoning_tokens and 'reasoning_tokens' in usage:
                reasoning_tokens = usage['reasoning_tokens']

        return model_answer, tokens_used, reasoning_tokens, reasoning_text, prompt_tokens, cached_tokens
    
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
            difficulty=question.get('difficulty'),
            is_enigma=question.get('type') == 'enigme',
            enigma_complexity=question.get('complexity') if question.get('type') == 'enigme' else None
        )