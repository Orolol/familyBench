# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TreeEval is a multi-language LLM evaluation tool that generates dynamic benchmarks to test relational reasoning capabilities. The project creates random family trees, converts them to textual descriptions, and generates question-answer pairs for evaluation. Supports French (fr) and English (en).

## Core Architecture

The system follows a pipeline architecture:
1. **Tree Generation** (`tree_generator.py`): Creates random family trees with configurable constraints
2. **Text Conversion** (`text_converter.py`): Converts trees to structured descriptions (French/English). Options: `shuffle` (seeded, default on), `relations` = mixed|parents|children|both (default `mixed`: each parent-child link stated once, random direction and place), `derived_links_percentage` (default 30: "X is the sister of Y" instead of parent links, anchor Y always explicit), a conventions line (brother = both parents in common) heads every description
3. **Question Generation** (`question_generator.py`): 23 question types in 4 difficulty tiers (easy/medium/hard/enigma), stratified sampling across types, `expert` mode; every question carries `type` and `difficulty`
4. **Model Evaluation** (`evaluate.py`): Async evaluation system for testing LLMs via OpenAI-compatible APIs
5. **CLI Scripts**: `generate_benchmark.py`, `evaluate.py`, `analyze_results.py` (placeholder)

Key modules:
- `models.py`: Core `Person` dataclass with unique constraints
- `translations.py`: Multi-language support system
- `versioning.py`: `GENERATOR_VERSION` and `benchmark_fingerprint()` (bump the version whenever a change alters the tree or questions produced for a given seed)
- `cache_manager.py`: optional `diskcache` cache of API responses (in-memory fallback)
- `evaluation/`: Complete async evaluation framework with answer cleaning, stats, and result formatting
- `questions/`: Modular question generation system with 23 question types including 9 enigma complexity levels (7-9 use the generic chain engine in `enigma.py`)
- `questions/rewrite.py`: post-selection difficulty rewrites: `anonymize_names` (names -> unique attribute description, never on enigmas), `convert_long_answers_to_counts` (> `max_answer_names` names -> counting question), `drop_census_questions`, `fix_english_articles`

## Common Commands

### Generate a benchmark
```bash
# Basic usage (French)
python generate_benchmark.py --people 30 --depth 3 --questions 50 --output benchmark.json

# English benchmark
python generate_benchmark.py --people 50 --depth 4 --questions 100 --language en --output benchmark_en.json

# Easier description / no rewrites (closer to the 2025 protocol)
python generate_benchmark.py --people 400 --depth 6 --questions 200 --seed 43 --language en --no-shuffle --relations both --max-answer-names 0 --anonymize-percentage 0 --output easy.json

# Generate with Markdown output for direct LLM prompting
python generate_benchmark.py --people 5 --depth 2 --questions 10 --md-output prompt.md

# Multi-family tree with enigmas
python generate_benchmark.py --people 60 --depth 4 --questions 100 --root-couples 3 --enigma-percentage 15 --output multi_family.json

# With custom seed for reproducibility
python generate_benchmark.py --people 50 --depth 4 --questions 100 --seed 12345 --output benchmark.json
```

### Evaluate models
```bash
# Run evaluation with default config
python evaluate.py

# Evaluate specific models
python evaluate.py --models gpt-3.5-turbo claude-3

# Evaluate on specific benchmarks
python evaluate.py --benchmarks small_fr large_en

# With custom configuration
python evaluate.py --config my_eval_config.yaml

# Overrides: batch size (questions per request), runs, concurrency, output dir, debug logging
python evaluate.py --batch-size 20 --runs 2 --max-concurrent 4 --output-dir evaluation_results/exp --debug

# Compare batch sizes on one model (accuracy vs cost)
python scripts/batch_sweep.py --config evaluation_config_batch_sweep.yaml --batch-sizes 1 5 10 20
```

### Development Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Format code (if black is installed)
black tree_evaluator/ *.py

# Type checking (if mypy is installed)
mypy tree_evaluator/

# Run tests (no network needed; the end-to-end test uses a local fake server)
pytest
```

## Important Constraints

When modifying the code, maintain these unique constraints:
- Each person must have a unique first name
- Professions are NOT unique — multiple people can share the same profession (intentional for attribute-search questions)
- The combination (hair_color, eye_color, hat_color) must be unique
- Each child has exactly 2 parents; a person may have children with up to two partners (`second_union_percentage`, default 20): half-siblings and step-parents exist. Sibling/uncle/cousin/nephew semantics live in `questions/base.py` (`get_siblings` = both parents in common, `get_half_siblings` = exactly one) and every question module must use these helpers
- Support both French and English throughout the codebase

## Output Formats

The system generates multiple output formats:
1. **JSON Benchmark**: Complete benchmark with metadata, questions, and answers
2. **Markdown Prompt**: LLM-ready prompt with instructions and questions (no answers)
3. **CSV Results**: Evaluation results with detailed metrics per question
4. **JSON Results**: Complete evaluation data including reasoning tokens and response times

## Question Types

21 types grouped in tiers (see `DIFFICULTY_TIERS` in `question_generator.py`):
- **easy**: direct/inverse relations, attribute search, counting
- **medium**: multi-criteria search, complex relations (grandparents, cousins...), cross-sectional, vertical (ancestors/descendants), complex counting
- **hard**: compound relation+attribute, multihop, conditional, negation, comparative, relational path, inverse complex search, vertical with criteria, half-siblings (`demi_fratrie`), step-parents/co-parents (`beaux_parents`)
- **enigma**: riddles of complexity 1 to 9 (`complexity` field). Levels with a discriminating attribute are phrased "Which son of X has black hair?" / "Quel fils de X a les cheveux noirs ?" so the attribute cannot be read as qualifying X

`--difficulty all` samples evenly across types (round-robin) with `enigma_percentage` enigmas; `expert` = hard tier (minus compound attributes and relational paths) + enigmas of complexity 4-9 (>= 40 % from 7-9).

Difficulty levers (generator 4.0, hard defaults): `max_children` (default 2), `second_union_percentage` (20), `derived_links_percentage` (30), `shuffle` (default true), `relations` (default `mixed`), `max_answer_names` (default 10, 0 disables), `drop_answer_names_above` (default 40: census questions removed before sampling), `anonymize_percentage` (default 50). All are CLI flags of `generate_benchmark.py` and keys of `benchmarks:` entries, and all are part of the benchmark fingerprint. Questions carry `answer_format`, `anonymized`, `converted_to_count`.

Answers are names sorted alphabetically and comma-separated, a number, or `None`/`Aucun`. `multihop` and `relational_path` are the only types whose answer can be an attribute value or a relation label instead of names.

## Evaluation System

The evaluation framework (`tree_evaluator/evaluation/`) includes:
- **Async API calls** with a concurrency semaphore (`max_concurrent_requests`), timeout and retries; SSE streaming by default (`stream: false` to disable; `idle_timeout` seconds without a chunk = stalled stream, counted as no-response and retried); empty or `finish_reason=length` responses are never cached and retries bypass the cache
- **Three request formats**: OpenAI chat completions (default, incl. OpenRouter `reasoning`/`provider`), OpenAI Responses API (when `reasoning` is set and `api_base` is OpenAI), Anthropic messages
- **Answer cleaning** to normalize LLM responses (handles JSON arrays, numbered lists, tags, etc.)
- **Scoring**: `is_correct` = exact set match OR Jaccard >= `ModelEvaluator.CORRECT_PARTIAL_THRESHOLD` (0.9); `hallucinated_names` counts names absent from the tree (only when the expected answer is a name list)
- **Stats**: accuracy, exact match, per-type, per-difficulty, enigma by complexity, hallucination rate, tokens, cost (if `pricing` given)
- **Reproducibility metadata** in `summary_*.json` and `detailed_*.json`: benchmark fingerprint, generator version, actual tree depth
- **Logging**: `evaluation_debug.log` (rotating, INFO by default, `--debug` for full requests/responses)

## Current Implementation Status

✅ Fully Implemented:
- Core tree generation with all constraints, actual-depth warning
- Text conversion with BFS ordering
- 23 question types, 6 enigma levels, difficulty tiers and stratified sampling
- Benchmark generation (JSON and Markdown) with fingerprint metadata
- Complete async evaluation system with cache, cost tracking and rich progress display
- Multi-language support (French/English)
- Results analysis CLI (`analyze_results.py`: per-type/per-tier stats, plots, HTML report)
- pytest suite in `tests/`

❌ Not implemented / known limits:
- The requested tree depth is an upper bound: the people pool is usually exhausted before reaching it
- Performance optimizations (pre-computed relations)
- Additional languages beyond French/English
- Historical 2025 leaderboard in README is not reproducible with the current data files (see README note)
