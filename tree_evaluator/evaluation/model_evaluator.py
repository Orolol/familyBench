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


class StalledStreamError(Exception):
    """Aucun chunk reçu pendant idle_timeout secondes sur un flux SSE."""


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
        # Température : absente => valeur par défaut du vendeur (Anthropic la
        # refuse avec le thinking, les modèles de raisonnement OpenAI l'ignorent).
        self.temperature = config.get('temperature')
        self.max_tokens = config.get('max_tokens', 64000)
        self.max_completion_tokens = config.get('max_completion_tokens')
        # Plafond de sortie PAR QUESTION (raisonnement + réponse). En batch, le
        # plafond de la requête est multiplié par le nombre de questions.
        self.max_tokens_per_question = config.get('max_tokens_per_question')
        self.language = 'fr'  # Will be set per benchmark
        self.reasoning_config = config.get('reasoning', None)
        self.provider_config = config.get('provider', None)
        # Niveau d'effort générique ("low"|"medium"|"high"|"xhigh"|"max"...), traduit
        # dans le paramètre propre à chaque API. Le libellé `thinking_level` est
        # la seconde dimension du leaderboard (paire modèle + niveau).
        self.effort = config.get('effort')
        self.thinking_level = str(config.get('thinking_level') or self.effort or 'default')
        # Où placer l'effort pour les API OpenAI-compatibles :
        #   "reasoning_effort" (défaut : OpenAI chat, Qwen, Moonshot K3, Z.ai, Gemini compat)
        #   "thinking"         (DeepSeek : thinking.reasoning_effort, vérifié dans la référence API)
        #   "none"             (ne rien envoyer, ex. modèle sans contrôle d'effort)
        self.effort_param = config.get('effort_param', 'reasoning_effort')
        # Vendeurs dont max_tokens ne couvre pas la chaîne de pensée (Qwen) : nom du
        # paramètre de budget de raisonnement, réglé à max_tokens_per_question x batch.
        self.budget_param = config.get('budget_param')
        # Paramètres bruts fusionnés dans le corps de la requête (budgets de
        # thinking propres à un vendeur, etc.)
        self.extra_body: Dict[str, Any] = dict(config.get('extra_body') or {})
        # Famille d'API : "anthropic" (Messages), "openai_responses", "openai_chat"
        # (OpenAI-compatible : OpenAI chat, OpenRouter, DeepSeek, Qwen, Moonshot, Z.ai, Gemini compat, local)
        self.api = config.get('api') or self._detect_api()
        self.anthropic_version = config.get('anthropic_version', '2023-06-01')
        # Clés liées à une identité : Anthropic exige l'en-tête anthropic-workspace-id
        self.anthropic_workspace_id = self._resolve_api_key(str(config.get('anthropic_workspace_id') or ''))
        # Streaming SSE pour les API chat/completions (défaut: activé). Évite les
        # coupures des réponses longues non streamées et permet de suivre la
        # progression dans les logs. Désactivé automatiquement pour Anthropic et
        # l'API Responses d'OpenAI.
        self.stream = bool(config.get('stream', True))
        self.stream_options = bool(config.get('stream_options', True))
        # Délai max sans aucun chunk reçu en streaming (secondes). Un flux figé
        # (fournisseur mort côté OpenRouter) est coupé et compté comme une
        # non-réponse, donc réessayé, au lieu d'attendre le timeout global.
        self.idle_timeout = int(config.get('idle_timeout', 300))
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

    def _detect_api(self) -> str:
        base = self.api_base.lower()
        if "anthropic" in base:
            return "anthropic"
        if "api.openai.com" in base and (self.reasoning_config or self.effort):
            return "openai_responses"
        return "openai_chat"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api == "anthropic":
            if self.api_key != "none":
                headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = self.anthropic_version
            if self.anthropic_workspace_id and self.anthropic_workspace_id != "none":
                headers["anthropic-workspace-id"] = self.anthropic_workspace_id
        elif self.api_key != "none":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _effective_max_tokens(self, n_questions: int = 1) -> int:
        """Plafond de sortie de la requête (raisonnement inclus)."""
        if self.max_tokens_per_question:
            return int(self.max_tokens_per_question) * max(1, n_questions)
        if self.max_completion_tokens:
            return int(self.max_completion_tokens)
        return int(self.max_tokens) if self.max_tokens is not None else 64000

    def entry_metadata(self) -> Dict[str, Any]:
        """Description de l'entrée du leaderboard (pour les résumés)."""
        return {
            "model": self.model,
            "api": self.api,
            "api_base": self.api_base,
            "thinking_level": self.thinking_level,
            "effort": self.effort,
            "effort_param": self.effort_param,
            "budget_param": self.budget_param,
            "reasoning": self.reasoning_config,
            "extra_body": self.extra_body or None,
            "max_tokens_per_question": self.max_tokens_per_question,
            "max_tokens": self._effective_max_tokens(1),
            "temperature": self.temperature,
            "provider_routing": self.provider_config,
        }

    def _resolve_api_key(self, key: str) -> str:
        """Résout les variables d'environnement dans la clé API."""
        if not key:
            return ''
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
                    tree_description, question, session, timeout, language, total_start_time,
                    use_cache=(attempt == 0),
                )

                # Si la réponse est valide, coupée par max_tokens (un retry aurait le
                # même sort) ou si c'est la dernière tentative, retourner
                if not result.no_response or result.finish_reason == "length" or attempt == max_retries - 1:
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
                                               total_start_time: float,
        use_cache: bool = True) -> EvaluationResult:
        """Évalue une question unique - une seule tentative.

        use_cache=False (retries) : on ignore le cache, sinon un retry rejouerait
        la même réponse vide/tronquée."""

        # Construire le prompt (préfixe stable = arbre, suffixe = question)
        parts = self.prompt_builder.single_question_parts(tree_description, question['question'], language)
        prompt = "\n\n".join(parts)

        # Mesurer le temps de réponse
        start_time = time.time()

        try:
            # Faire l'appel API
            headers = self._headers()
            # Adapter le format selon le type d'API
            data = self._build_api_request(prompt, language, batch=False, parts=parts, n_questions=1)
            url = self._get_api_url()

            # Vérifier le cache
            cache_key = {
                "model": self.name,
                "url": url,
                "data": data
            }
            cached_response = self.cache_manager.get(cache_key) if use_cache else None
            if cached_response:
                logger.info(f"Cache hit for {self.name} - Question {question['id']}")
                result = cached_response
                # Simuler un temps de réponse nul ou très court pour le cache
                response_time = 0.001
            else:
                # Log de la requête envoyée
                logger.debug(f"Sending request to {url} for {self.name}")
                logger.debug(f"Request data: {json.dumps(data, indent=2)}")

                status, result = await self._call_api(
                    session, url, data, headers, timeout, f"question {question['id']}"
                )
                response_time = time.time() - start_time
                if status != 200:
                    logger.error(f"API Error {status} for {self.name}: {result}")
                    return self._create_error_result(
                        question, f"API Error {status}: {result}", response_time
                    )

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

            finish_reason = self._finish_reason(result)
            # Mettre en cache seulement les réponses exploitables (non vides, non tronquées)
            if not cached_response and model_answer and finish_reason != "length":
                self.cache_manager.set(cache_key, result)

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
                finish_reason=finish_reason,
                thinking_level=self.thinking_level,
                provider=result.get('provider') if isinstance(result, dict) else None,
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

        except StalledStreamError as e:
            logger.warning(f"Stalled stream for {self.name} on question {question['id']}: {e}")
            return self._create_error_result(question, f"Stalled stream: {e}", time.time() - total_start_time, no_response=True)
        except asyncio.TimeoutError:
            logger.error(f"Timeout after {timeout}s for {self.name} on question {question['id']}")
            return self._create_error_result(question, "Timeout", time.time() - total_start_time)
        except (aiohttp.ClientError, ConnectionError, OSError) as e:
            # Connexion coupée par le fournisseur : transitoire, donc réessayé (no_response=True)
            logger.warning(f"Connection error for {self.name} on question {question['id']}: {e}")
            return self._create_error_result(question, f"Connection error: {e}", time.time() - total_start_time, no_response=True)
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
                    tree_description, questions, session, timeout, language, total_start_time,
                    use_cache=(attempt == 0),
                )

                # Vérifier si toutes les réponses sont vides
                all_empty = all(r.no_response for r in results)

                truncated = all(r.finish_reason == "length" for r in results)
                # Si au moins une réponse est valide, si la génération a été coupée par
                # max_tokens (un retry aurait le même sort) ou si c'est la dernière tentative
                if not all_empty or truncated or attempt == max_retries - 1:
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
                                                     total_start_time: float,
        use_cache: bool = True) -> List[EvaluationResult]:
        """Évalue un batch de questions en une seule requête - une seule tentative."""

        # Construire le prompt pour plusieurs questions (préfixe stable = arbre)
        parts = self.prompt_builder.batch_prompt_parts(tree_description, questions, language)
        prompt = "\n\n".join(parts)

        # Mesurer le temps de réponse
        start_time = time.time()

        try:
            # Faire l'appel API
            headers = self._headers()
            # Adapter le format selon le type d'API
            data = self._build_api_request(prompt, language, batch=True, parts=parts, n_questions=len(questions))
            url = self._get_api_url()

            # Vérifier le cache
            cache_key = {
                "model": self.name,
                "url": url,
                "data": data
            }
            cached_response = self.cache_manager.get(cache_key) if use_cache else None
            if cached_response:
                logger.info(f"Cache hit for {self.name} - Batch of {len(questions)} questions")
                result = cached_response
                response_time = 0.001
            else:
                # Log de la requête envoyée
                logger.debug(f"Sending request to {url} for {self.name}")
                logger.debug(f"Request data: {json.dumps(data, indent=2)}")

                status, result = await self._call_api(
                    session, url, data, headers, timeout, f"batch of {len(questions)}"
                )
                response_time = time.time() - start_time
                if status != 200:
                    logger.error(f"API Error {status} for {self.name}: {result}")
                    # Retourner des erreurs pour toutes les questions du batch
                    return [self._create_error_result(
                        q, f"API Error {status}: {result}",
                        (time.time() - total_start_time) / len(questions)
                    ) for q in questions]

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
            finish_reason = self._finish_reason(result)
            if not any(answers):
                logger.warning(f"Could not parse any answer from batch response for {self.name}: {model_response[:300]!r}")
            # Mettre en cache seulement les réponses exploitables (non vides, non tronquées)
            if not cached_response and any(answers) and finish_reason != "length":
                self.cache_manager.set(cache_key, result)

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
                    finish_reason=finish_reason,
                    thinking_level=self.thinking_level,
                    provider=result.get('provider') if isinstance(result, dict) else None,
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

        except StalledStreamError as e:
            logger.warning(f"Stalled stream for {self.name} on batch of {len(questions)}: {e}")
            return [self._create_error_result(
                q, f"Stalled stream: {e}", (time.time() - total_start_time) / len(questions), no_response=True
            ) for q in questions]
        except asyncio.TimeoutError:
            logger.error(f"Timeout after {timeout}s for {self.name} on batch of {len(questions)}")
            return [self._create_error_result(
                q, "Timeout", (time.time() - total_start_time) / len(questions)
            ) for q in questions]
        except (aiohttp.ClientError, ConnectionError, OSError) as e:
            logger.warning(f"Connection error for {self.name} on batch of {len(questions)}: {e}")
            return [self._create_error_result(
                q, f"Connection error: {e}", (time.time() - total_start_time) / len(questions), no_response=True
            ) for q in questions]

        except Exception as e:
            return [self._create_error_result(
                q, str(e), (time.time() - total_start_time) / len(questions)
            ) for q in questions]

    @staticmethod
    def _finish_reason(result: Dict[str, Any]) -> Optional[str]:
        choices = result.get("choices") if isinstance(result, dict) else None
        if choices and isinstance(choices[0], dict):
            return choices[0].get("finish_reason") or choices[0].get("stop_reason")
        if isinstance(result, dict):
            return result.get("stop_reason")  # Anthropic
        return None

    def _uses_streaming(self) -> bool:
        return bool(self.stream)

    @staticmethod
    def _anthropic_usage(usage: Dict[str, Any]) -> Dict[str, Any]:
        cached = int(usage.get("cache_read_input_tokens") or 0)
        created = int(usage.get("cache_creation_input_tokens") or 0)
        return {
            "prompt_tokens": int(usage.get("input_tokens") or 0) + cached + created,
            "completion_tokens": int(usage.get("output_tokens") or 0),
            "prompt_tokens_details": {"cached_tokens": cached, "cache_creation_tokens": created},
        }

    @staticmethod
    def _anthropic_stop(stop_reason: Optional[str]) -> Optional[str]:
        return {"end_turn": "stop", "max_tokens": "length", "stop_sequence": "stop"}.get(stop_reason, stop_reason)

    @staticmethod
    def _chat_shape(content: str, reasoning: str, usage: Dict[str, Any], finish_reason: Optional[str],
                    provider: Optional[str] = None, streamed: bool = False) -> Dict[str, Any]:
        message: Dict[str, Any] = {"role": "assistant", "content": content}
        if reasoning:
            message["reasoning"] = reasoning
        return {
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            "usage": usage,
            "provider": provider,
            "streamed": streamed,
        }

    @classmethod
    def _normalize_anthropic(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Réponse Messages (non streamée) -> forme chat/completions."""
        text_parts, thinking_parts = [], []
        for block in raw.get("content") or []:
            if block.get("type") == "text":
                text_parts.append(block.get("text") or "")
            elif block.get("type") == "thinking":
                thinking_parts.append(block.get("thinking") or "")
        return cls._chat_shape("".join(text_parts), "".join(thinking_parts),
                               cls._anthropic_usage(raw.get("usage") or {}),
                               cls._anthropic_stop(raw.get("stop_reason")), provider="anthropic")

    @classmethod
    def _normalize_responses(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Réponse de l'API Responses (non streamée ou événement completed) -> forme chat/completions."""
        text_parts, reasoning_parts = [], []
        for item in raw.get("output") or []:
            if item.get("type") == "message":
                for part in item.get("content") or []:
                    if part.get("type") == "output_text":
                        text_parts.append(part.get("text") or "")
            elif item.get("type") == "reasoning":
                for part in item.get("summary") or []:
                    reasoning_parts.append(part.get("text") or "")
        usage = raw.get("usage") or {}
        incomplete = (raw.get("incomplete_details") or {}).get("reason")
        status = raw.get("status")
        finish = "length" if incomplete == "max_output_tokens" else ("stop" if status in (None, "completed") else status)
        return cls._chat_shape(
            raw.get("output_text") or "".join(text_parts), "".join(reasoning_parts),
            {
                "prompt_tokens": int(usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("output_tokens") or 0),
                "prompt_tokens_details": {"cached_tokens": int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0)},
                "completion_tokens_details": {"reasoning_tokens": int((usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)},
            },
            finish, provider="openai",
        )

    def _normalize_raw(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if self.api == "anthropic":
            return self._normalize_anthropic(raw)
        if self.api == "openai_responses":
            return self._normalize_responses(raw)
        return raw

    async def _call_api(self, session: aiohttp.ClientSession, url: str, data: Dict[str, Any],
                        headers: Dict[str, str], timeout: int, label: str) -> tuple[int, Any]:
        """POST l'appel API. Retourne (status, result_dict) ou (status, error_text).

        En streaming, les événements SSE de chaque famille d'API (chat/completions,
        Anthropic Messages, OpenAI Responses) sont ré-assemblés en une réponse au
        format chat/completions pour que scoring et cache restent identiques.
        """
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        if not self._uses_streaming():
            async with session.post(url, json=data, headers=headers, timeout=client_timeout) as response:
                if response.status != 200:
                    return response.status, await response.text()
                return 200, self._normalize_raw(await response.json())

        payload = dict(data)
        payload["stream"] = True
        if self.api == "openai_chat" and self.stream_options:
            payload["stream_options"] = {"include_usage": True}
        acc: Dict[str, Any] = {
            "content": [], "reasoning": [], "usage": {}, "finish_reason": None,
            "provider": None, "role": "assistant", "error": None,
        }
        started = time.time()
        last_log = started
        last_progress = started
        stream_timeout = aiohttp.ClientTimeout(total=timeout, sock_read=self.idle_timeout)
        async with session.post(url, json=payload, headers=headers, timeout=stream_timeout) as response:
            if response.status != 200:
                return response.status, await response.text()
            if "json" in (response.headers.get("Content-Type") or "").lower():
                # Le serveur a ignoré `stream` (proxy, serveur local minimal) : réponse classique
                return 200, self._normalize_raw(await response.json())
            buffer = b""
            try:
                async for chunk in response.content.iter_any():
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if not line or line.startswith(b":") or not line.startswith(b"data:"):
                            continue  # keep-alive, commentaire SSE ou ligne "event:"
                        body = line[5:].strip()
                        if body == b"[DONE]":
                            continue
                        try:
                            event = json.loads(body)
                        except ValueError:
                            logger.debug(f"Unparseable SSE line for {self.name}: {body[:200]!r}")
                            continue
                        if self._consume_event(event, acc):
                            last_progress = time.time()
                        if acc["error"] is not None:
                            return 500, json.dumps(acc["error"])
                    now = time.time()
                    # Les keep-alive (": OPENROUTER PROCESSING", ping Anthropic) ne sont
                    # pas une progression : sans token pendant idle_timeout, on coupe.
                    if now - last_progress >= self.idle_timeout:
                        raise StalledStreamError(
                            f"no tokens for {int(now - last_progress)}s (keep-alives only) after "
                            f"{sum(map(len, acc['reasoning']))} reasoning chars and {sum(map(len, acc['content']))} answer chars"
                        )
                    if now - last_log >= 60:
                        last_log = now
                        logger.info(
                            f"Streaming {label} for {self.name}: {int(now - started)}s, "
                            f"{sum(map(len, acc['reasoning']))} reasoning chars, {sum(map(len, acc['content']))} answer chars"
                        )
            except asyncio.TimeoutError:
                idle = time.time() - last_progress
                if idle >= self.idle_timeout - 1 and time.time() - started < timeout - 1:
                    raise StalledStreamError(
                        f"no data for {int(idle)}s after {sum(map(len, acc['reasoning']))} reasoning chars "
                        f"and {sum(map(len, acc['content']))} answer chars"
                    )
                raise
        if acc["finish_reason"] == "length":
            logger.warning(f"{self.name} {label}: generation stopped by max_tokens (finish_reason=length)")
        return 200, self._chat_shape(
            "".join(acc["content"]), "".join(acc["reasoning"]), acc["usage"], acc["finish_reason"],
            provider=acc["provider"] or ("anthropic" if self.api == "anthropic" else None), streamed=True,
        )

    def _consume_event(self, event: Dict[str, Any], acc: Dict[str, Any]) -> bool:
        """Intègre un événement SSE dans l'accumulateur. Retourne True si des tokens sont arrivés."""
        progressed = False
        if self.api == "anthropic":
            etype = event.get("type")
            if etype == "error":
                acc["error"] = event.get("error") or {"message": "unknown error"}
            elif etype == "message_start":
                acc["usage"] = self._anthropic_usage((event.get("message") or {}).get("usage") or {})
            elif etype == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta" and delta.get("text"):
                    acc["content"].append(delta["text"]); progressed = True
                elif delta.get("type") == "thinking_delta" and delta.get("thinking"):
                    acc["reasoning"].append(delta["thinking"]); progressed = True
            elif etype == "message_delta":
                delta = event.get("delta") or {}
                if delta.get("stop_reason"):
                    acc["finish_reason"] = self._anthropic_stop(delta["stop_reason"])
                usage = event.get("usage") or {}
                if usage:
                    merged = dict(acc["usage"] or {})
                    if any(k in usage for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")):
                        base = {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
                        base.update({k: v for k, v in usage.items() if v is not None})
                        merged.update(self._anthropic_usage(base))
                    if usage.get("output_tokens") is not None:
                        merged["completion_tokens"] = int(usage["output_tokens"])
                    acc["usage"] = merged
            return progressed
        if self.api == "openai_responses":
            etype = event.get("type") or ""
            if etype in ("error", "response.failed"):
                acc["error"] = event.get("error") or (event.get("response") or {}).get("error") or {"message": "response failed"}
            elif etype == "response.output_text.delta" and event.get("delta"):
                acc["content"].append(event["delta"]); progressed = True
            elif etype == "response.reasoning_summary_text.delta" and event.get("delta"):
                acc["reasoning"].append(event["delta"]); progressed = True
            elif etype in ("response.completed", "response.incomplete"):
                norm = self._normalize_responses(event.get("response") or {})
                acc["usage"] = norm["usage"]
                acc["finish_reason"] = norm["choices"][0]["finish_reason"]
                acc["provider"] = "openai"
            return progressed
        # openai_chat (OpenAI, OpenRouter, DeepSeek, Qwen, Moonshot, Z.ai, Gemini compat, local)
        if event.get("usage"):
            acc["usage"] = event["usage"]
        if event.get("provider"):
            acc["provider"] = event["provider"]
        if event.get("error"):
            acc["error"] = event["error"]
        for choice in event.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("role"):
                acc["role"] = delta["role"]
            text = delta.get("content")
            if isinstance(text, str) and text:
                acc["content"].append(text); progressed = True
            got_reasoning = False
            for key in ("reasoning", "reasoning_content"):
                rt = delta.get(key)
                if isinstance(rt, str) and rt:
                    acc["reasoning"].append(rt); progressed = True; got_reasoning = True
            if not got_reasoning:
                # OpenRouter : choices[].delta.reasoning_details = [{type: "reasoning.text", text}, {type: "reasoning.summary", summary}]
                for item in delta.get("reasoning_details") or []:
                    if isinstance(item, dict):
                        rt = item.get("text") or item.get("summary")
                        if isinstance(rt, str) and rt:
                            acc["reasoning"].append(rt); progressed = True
            if choice.get("finish_reason"):
                acc["finish_reason"] = choice["finish_reason"]
        return progressed

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

    def _build_api_request(self, prompt: str, language: str, batch: bool = False,
                           parts: Optional[tuple] = None, n_questions: int = 1) -> Dict[str, Any]:
        """Construit la requête selon la famille d'API.

        `parts` = (préfixe stable, suffixe variable) ; sinon `prompt` entier.
        """
        prefix, suffix = parts if parts else (None, prompt)
        system_prompt = self.prompt_builder.get_system_prompt(language, batch)
        max_tokens = self._effective_max_tokens(n_questions)

        if self.api == "anthropic":
            # Arbre dans un bloc système marqué cache_control (préfixe stable),
            # question dans le message utilisateur. Thinking adaptatif, effort via
            # output_config ; ni température ni budget en tokens.
            system_blocks: List[Dict[str, Any]] = [{"type": "text", "text": system_prompt}]
            if prefix:
                system_blocks.append({"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}})
            else:
                system_blocks[0]["cache_control"] = {"type": "ephemeral"}
            data: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system_blocks,
                "messages": [{"role": "user", "content": suffix if prefix else prompt}],
                "thinking": {"type": "adaptive"},
            }
            if self.effort:
                data["output_config"] = {"effort": self.effort}
            data.update(self.extra_body)
            return data

        if self.api == "openai_responses":
            data = {
                "model": self.model,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_output_tokens": max_tokens,
            }
            reasoning = dict(self.reasoning_config or {})
            if self.effort and "effort" not in reasoning:
                reasoning["effort"] = self.effort
            if reasoning:
                data["reasoning"] = reasoning
            data.update(self.extra_body)
            return data

        # openai_chat
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        if self.temperature is not None:
            data["temperature"] = self.temperature
        if self.max_completion_tokens and not self.max_tokens_per_question:
            data["max_completion_tokens"] = max_tokens
        else:
            data["max_tokens"] = max_tokens
        if "openrouter" in self.api_base:
            reasoning = dict(self.reasoning_config or {})
            if self.effort and "effort" not in reasoning and "max_tokens" not in reasoning:
                reasoning["effort"] = self.effort
            if reasoning:
                data["reasoning"] = reasoning
            if self.provider_config:
                data["provider"] = self.provider_config
        else:
            if self.effort and self.effort_param == "reasoning_effort":
                data["reasoning_effort"] = self.effort
            if self.reasoning_config:
                data["reasoning"] = self.reasoning_config
        data.update(self.extra_body)
        if self.budget_param and self.max_tokens_per_question:
            data[self.budget_param] = int(self.max_tokens_per_question) * max(1, n_questions)
        if self.effort and self.effort_param == "thinking" and "openrouter" not in self.api_base:
            thinking = dict(data.get("thinking") or {"type": "enabled"})
            thinking["reasoning_effort"] = self.effort
            data["thinking"] = thinking
        return data

    def _get_api_url(self) -> str:
        """Retourne l'URL de l'API selon la famille."""
        if self.api == "anthropic":
            return f"{self.api_base}/messages"
        if self.api == "openai_responses":
            return f"{self.api_base}/responses"
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

        if "content" in result and "choices" not in result:  # Messages brut (non normalisé)
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
            cached_tokens = int(
                (in_details or {}).get('cached_tokens')          # OpenAI, Qwen, Z.ai, OpenRouter, Anthropic (normalisé)
                or usage.get('prompt_cache_hit_tokens')           # DeepSeek
                or usage.get('cached_tokens')                     # Moonshot
                or 0
            )
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
            thinking_level=self.thinking_level,
            is_enigma=question.get('type') == 'enigme',
            enigma_complexity=question.get('complexity') if question.get('type') == 'enigme' else None
        )