# FamilyBench 🌳

FamilyBench is an evaluation tool for testing the relational reasoning capabilities of Large Language Models (LLMs). It generates random family trees, converts them to textual descriptions, and creates question-answer pairs to evaluate understanding of complex family relationships.

## 🎯 Objective

FamilyBench enables systematic and reproducible evaluation of LLMs' ability to:
- Understand direct family relationships (parents, children)
- Infer complex relationships (grandparents, cousins, uncles/aunts)
- Reason across multiple generations
- Combine relationships with attributes (profession, physical appearance)
- Perform cross-sectional and vertical queries in the family tree

## 🌟 Features

- **Dynamic generation**: Creation of random family trees with configurable constraints
- **Multi-language**: Support for French and English
- **Varied question types**: 21 question types grouped in 4 difficulty tiers (easy, medium, hard, enigma), 9 enigma levels, plus an `expert` mode
- **Difficulty levers**: shuffled one-directional descriptions, attribute-based references instead of names, long answers turned into counts
- **Scoring you can audit**: exact match, Jaccard partial match, hallucination detection (invented names), per-type and per-tier accuracy
- **Reproducible**: seeds plus a benchmark fingerprint (generator version + data files + parameters) written in every output
- **Automatic evaluation**: Interface with OpenAI-compatible APIs to test multiple models
- **Flexible export**: JSON and Markdown formats for direct LLM integration

## 📋 Prerequisites

- Python 3.8+
- pip

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/familybench.git
cd familybench
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) For automatic evaluation, create a `.env` file:
```bash
OPENROUTER_API_KEY=your_api_key_here
# Or any other required API key
```

## 📖 Usage

### Benchmark Generation

#### Basic Usage
```bash
# Generate a simple benchmark in French
python generate_benchmark.py --people 30 --depth 3 --questions 50 --output benchmark.json

# Generate a benchmark in English
python generate_benchmark.py --people 50 --depth 4 --questions 100 --language en --output benchmark_en.json
```

#### Generation for Direct Prompting
```bash
# Generate a ready-to-use Markdown file for an LLM
python generate_benchmark.py --people 20 --depth 3 --questions 30 --md-output prompt.md
```

#### Advanced Options
```bash
# With seed for reproducibility
python generate_benchmark.py --people 100 --depth 5 --questions 200 --seed 12345 --output benchmark_large.json

# With multiple families (root couples)
python generate_benchmark.py --people 60 --depth 4 --questions 100 --root-couples 3 --output multi_family.json

# Limit number of children per person
python generate_benchmark.py --people 40 --depth 3 --questions 80 --max-children 2 --output limited_children.json

# Only hard questions, or the expert mix (hard questions + complexity 4-6 enigmas)
python generate_benchmark.py --people 300 --depth 6 --questions 100 --root-couples 4 --difficulty hard --output hard.json
python generate_benchmark.py --people 300 --depth 6 --questions 100 --root-couples 4 --difficulty expert --output expert.json
```

#### Difficulty levers (generator ≥ 3.0)

These options apply both to `generate_benchmark.py` flags and to `benchmarks:` entries in the evaluation config. The defaults are the hard settings.

| Lever | Flag / config key | Default | Effect |
|---|---|---|---|
| Second unions | `--second-union-percentage P` / `second_union_percentage:` | 20 | P % of people also have children with a second partner. This creates half-siblings and step-parents; "brother/sister" means both parents in common, "half-brother/half-sister" exactly one (the convention is written at the top of every description). New question types `demi_fratrie` and `beaux_parents`. `0` restores the single-union tree. |
| Deeper trees | `--max-children N` / `max_children:` | 2 | Maximum children per union. 2 instead of 3 gives more generations for the same number of people, hence longer ancestor chains. |
| Mixed-direction links | `--relations mixed` / `relations: mixed` | `mixed` | Every parent-child link is stated exactly once, in a random direction and place: "Ana is the mother of Leo" here, "Leo is the son of Marc" forty lines later. Knowing both parents of someone means joining two distant sentences. `parents`, `children` and `both` remain available. |
| Derived links | `--derived-links-percentage P` / `derived_links_percentage:` | 30 | P % of people are described only as "X is the sister of Y" instead of through their parents; Y keeps explicit links and is never derived itself, so the tree stays fully reconstructible (checked by a test). |
| Shuffled description | `--no-shuffle` / `shuffle: false` | shuffled | Sorted output (by generation, then name) leaks everyone's generation and keeps parents next to children. The shuffle is seeded from the benchmark seed, so the description is byte-identical across runs and provider prompt caches keep hitting. |
| Long answers become counts | `--max-answer-names N` / `max_answer_names:` | 10 | A question whose answer would list more than N names is rewritten as *"How many people answer the following question: …"* with a numeric answer. Enumeration stamina is no longer rewarded, and partial credit cannot inflate the score. `0` disables. |
| Census questions dropped | `--drop-answer-names-above N` / `drop_answer_names_above:` | 40 | Questions whose answer would list more than N names are removed before sampling. Counting them instead does not remove the work: "who has the same number of children as X" on 1,000 people is a full census that eats the whole reasoning budget. `0` disables. |
| Attribute references | `--anonymize-percentage P` / `anonymize_percentage:` | 50 | In P % of questions, every first name is replaced by the person's unique attribute description (*"the person with red hair, blue eyes and a green hat"*), so the model must locate the person before reasoning. Enigmas are never anonymized (their own phrasing already does this at levels 6 and 8). |
| Enigma levels 7-9 | via `difficulty: expert` or `enigma` | | 7: 3-relation chain from a named person + discriminating attribute. 8: same chain from an attribute-described person. 9: two chains joined by an attribute equality (*"the female cousin of X who has the same eye color as the grandmother of Y"*). `expert` now draws enigmas from levels 4-9 with at least 40 % from 7-9. |

Every generated question records `difficulty`, `answer_format` (`names`, `count`, `label`, `none`), `anonymized` and `converted_to_count`, so results can be sliced by lever.

```bash
# Easier, closer to the 2025 protocol
python generate_benchmark.py --people 400 --depth 6 --questions 200 --seed 43 --language en \
    --no-shuffle --relations both --max-children 3 --second-union-percentage 0 --derived-links-percentage 0 \
    --max-answer-names 0 --anonymize-percentage 0 --output easy.json
```

> **Depth**: the requested depth is an upper bound. Each couple has 1 to `--max-children` children, so the pool of people is often exhausted before the requested depth (400 people with 10 root couples give 4 generations). The CLI prints a warning and writes `tree_depth_actual` in the metadata.

### Model Evaluation

#### Configuration
Create or modify `evaluation_config.yaml`:

```yaml
models:
  - name: "gpt-3.5-turbo"
    api_base: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-3.5-turbo"
    temperature: 0.0
    max_tokens: 1000

benchmarks:
  - name: "small_fr"
    people: 30
    depth: 3
    questions: 50
    language: "fr"
    seed: 42
    
  - name: "expert_en"
    people: 500
    depth: 6
    questions: 100
    root_couples: 4
    language: "en"
    seed: 1
    difficulty: expert      # all | easy | medium | hard | enigma | expert
    # Difficulty levers (defaults shown, see "Difficulty levers" above)
    shuffle: true
    relations: mixed        # mixed | parents | children | both
    max_children: 2
    second_union_percentage: 20
    derived_links_percentage: 30
    max_answer_names: 10
    drop_answer_names_above: 40
    anonymize_percentage: 50

evaluation:
  runs_per_benchmark: 1
  max_concurrent_requests: 10
  timeout: 600
  batch_size: 1
  output_dir: "evaluation_results"
  output_formats: [csv, json]
```

#### Leaderboard entries are (model, thinking level) pairs

Thinking effort is not comparable across vendors, so the benchmark does not pretend it is: an entry is a model **and** a thinking level, named like `claude-opus-5@high`, and both are reported (`thinking_level` on every result row, `entries` in every summary). Per-entry keys:

| Key | Meaning |
|---|---|
| `api` | `anthropic` (Messages API), `openai_responses`, or `openai_chat` (any OpenAI-compatible endpoint: OpenAI chat, OpenRouter, DeepSeek, Qwen/DashScope, Moonshot, Z.ai, Gemini's compat endpoint, local servers). Auto-detected from `api_base` when omitted. |
| `effort` | Generic effort label, translated into the vendor parameter: `output_config.effort` (Anthropic, with adaptive thinking), `reasoning.effort` (OpenAI Responses), `reasoning_effort` (OpenAI-compatible vendors), `reasoning: {effort}` (OpenRouter). |
| `effort_param` | Where OpenAI-compatible vendors expect the effort: `reasoning_effort` (default: OpenAI chat, Qwen, Moonshot K3, Z.ai, Gemini) or `thinking` (DeepSeek: `thinking.reasoning_effort`), or `none`. |
| `thinking_level` | Label shown in the leaderboard (defaults to `effort`). |
| `max_tokens_per_question` | Output cap (reasoning + answer) per question; the request cap is this times the batch size. The only budget notion that is portable across vendors. |
| `extra_body` | Vendor-specific parameters merged into the request, e.g. `thinking: {type: enabled}` for DeepSeek, Moonshot K2.6 and GLM, or Gemini's `google.thinking_config`. |
| `reasoning`, `provider` | OpenRouter-style reasoning object and provider routing (`order`, `allow_fallbacks`). |
| `pricing` | `input_per_mtok`, `output_per_mtok`, `cached_input_per_mtok` to get `cost_usd`. |
| `stream`, `idle_timeout` | Streaming is on for every API family; a stream without tokens for `idle_timeout` seconds is cut and retried. |

No temperature is sent unless `temperature` is set explicitly (Anthropic rejects it with thinking, reasoning models ignore it). On Anthropic the tree description goes into a system block marked `cache_control`, so the prefix is served from cache across questions; OpenAI-compatible vendors cache the identical prefix automatically. Per-vendor cache fields (`cached_tokens`, DeepSeek's `prompt_cache_hit_tokens`, Moonshot's `usage.cached_tokens`, Anthropic's `cache_read_input_tokens`) all land in `cached_tokens`. Use `api_key: "none"` for a local server without authentication.

`evaluation_config_hard_v4.yaml` is the reference protocol: hard tier only, 60 questions, batch 5, 16k output tokens per question, one entry per vendor with the exact parameter names each official API expects.

#### Running Evaluation
```bash
# Evaluate all models on all benchmarks
python evaluate.py

# Evaluate specific models
python evaluate.py --models gpt-3.5-turbo claude-3

# Evaluate on specific benchmarks
python evaluate.py --benchmarks small_fr large_en

# With custom configuration
python evaluate.py --config my_eval_config.yaml

# Full request/response logging (large!) in evaluation_debug.log
python evaluate.py --debug
```

#### Batch mode (cost control)

With `batch_size: 1` every question is a separate request that carries the whole tree description, so prompt tokens dominate the bill (about 48k tokens per question on a 500-person tree). With `batch_size: N` the tree is sent once for N questions; the model answers with a JSON object keyed by question number, so a skipped question does not shift the others. Missing answers count as no-responses.

```bash
python evaluate.py --batch-size 20            # override evaluation.batch_size
python evaluate.py --runs 3 --max-concurrent 4 --output-dir evaluation_results/exp1
```

To measure what batching costs in accuracy for a given model, run the same benchmark with several batch sizes and compare:

```bash
python scripts/batch_sweep.py --config evaluation_config_batch_sweep.yaml --batch-sizes 1 5 10 20
python scripts/batch_sweep.py --report-only evaluation_results/batch_sweep   # re-print the table
```

The report shows, per batch size: accuracy, exact match, no-response and error rates, hallucination rate, prompt / completion / reasoning tokens, cost, accuracy per difficulty tier, and the question-by-question agreement with the smallest batch size (questions lost and gained). In batch mode `response_time`, `tokens_used` and `reasoning_tokens` are averaged over the questions of the batch, and `reasoning_text` is shared. Every result row carries `batch_size`, and `analyze_results.py` groups by it automatically when several sizes are mixed.

Each run writes `partial_<ts>.jsonl` incrementally (one line per question as soon as it is scored, so a killed run loses nothing; `analyze_results.py` reads it), then `results_<ts>.csv/json` (one row per question), `detailed_<ts>.json` (system prompt, tree description and every Q&A, enough to replay the run) and `summary_<ts>.json` (per-model stats, per-type and per-tier accuracy, hallucination rate, benchmark fingerprint and actual tree depth). API responses are cached in `.cache/` when `diskcache` is installed, so re-running an identical request costs nothing.

### Results Analysis

```bash
# Analyze evaluation results
python analyze_results.py evaluation_results/results_*.csv

# Generate comparative plots
python analyze_results.py evaluation_results/results_*.csv --plots

# Export detailed report
python analyze_results.py evaluation_results/results_*.csv --report report.html

# Ignore files where every row is an error (API server down)
python analyze_results.py evaluation_results/results_*.csv --exclude-failed-runs
```

### Scoring

For each question the model answer is normalised (JSON arrays, numbered lists, `<answer>` tags, "Final answer:" prefixes, spelled-out numbers, `None`/`Aucun` variants) and compared to the expected answer as a **set of names**:

| Metric | Definition |
|---|---|
| `is_exact_match` | Same set of names (order ignored) |
| `partial_match_score` | Jaccard index between the two sets (1.0 for single answers that match) |
| `is_correct` | Exact match **or** Jaccard ≥ 0.9. On short lists this is equivalent to exact match; on lists of 10+ names it tolerates one missing or extra name |
| `no_response` | Empty answer, refusal, or a sentence instead of an answer |
| `hallucinated_names` | Names in the answer that do not exist in the tree (only computed when the expected answer is a list of names) |

Since generator 3.0, answers longer than `max_answer_names` are asked as counts, so partial credit only ever applies to lists of at most 10 names.

`accuracy` in the summaries is the share of `is_correct` answers over all questions, errors and no-responses included.

## 🧠 Question Types

FamilyBench generates 23 question types, grouped in difficulty tiers. `--difficulty all` (default) samples questions **evenly across types** with `--enigma-percentage` enigmas; `easy`, `medium`, `hard` and `enigma` restrict to one tier; `expert` mixes the hard tier (minus compound attributes and relational paths) with enigmas of complexity 4 to 9, at least 40 % of them being complexity 7 to 9.

| Tier | Types | Example |
|---|---|---|
| **easy** | `relation_directe`, `relation_inverse`, `recherche_attributs`, `comptage` | "Who are Marie's children?", "How many children does Pierre have?" |
| **medium** | `recherche_multi_criteres`, `relation_complexe`, `transversale_generation`, `verticale_ancetre`, `verticale_racine`, `verticale_feuille`, `verticale_descendant`, `comptage_complexe` | "Who are Sophie's cousins?", "Who is in the same generation as Luc and works as a doctor?" |
| **hard** | `relation_attribut_composee`, `multihop`, `conditional`, `negation`, `comparative`, `relational_path`, `recherche_inversee_complexe`, `verticale_descendant_critere`, `verticale_racine_critere`, `demi_fratrie`, `beaux_parents` | "Which of Paul's children work as engineers?", "Who has more grandsons than granddaughters?" |
| **enigma** | `enigme` (complexity 1 to 9) | "Which child of the son of Ken has red hair?", "Who is the female cousin of X who has the same eye color as the grandmother of Y?" |

Every generated question carries `type`, `difficulty` and, for enigmas, `complexity`. Answers are a single name, an alphabetically sorted comma-separated list, a number, or `None` / `Aucun`.

## 📊 Data Structure

### JSON Output Format
```json
{
  "tree_description": "Textual description of the family tree...",
  "prompt_template": "Template for LLM prompt",
  "questions": [
    {
      "id": 1,
      "question": "Who are Marie's parents?",
      "answer": "Jean,Sophie",
      "type": "relation_directe"
    }
  ],
  "metadata": {
    "total_people": 30,
    "tree_depth": 3,
    "tree_depth_actual": 3,
    "seed": 42,
    "language": "en",
    "difficulty": "all",
    "questions_requested": 50,
    "questions_generated": 50,
    "generator_version": "2.0",
    "benchmark_fingerprint": "28d22d39d3b571b8",
    "generation_timestamp": "2024-01-15T10:30:00"
  }
}
```

### Generation Constraints

- **Name uniqueness**: Each person has a unique first name
- **Profession uniqueness**: Professions are NOT unique — multiple people can share the same profession (intentional for attribute-search questions)
- **Appearance uniqueness**: The combination (hair, eyes, hat) is unique
- **Structure**: each child has exactly 2 parents; a person may have children with up to two partners (`second_union_percentage`), which creates half-siblings and step-parents

## 🌍 Multi-language Support

FamilyBench currently supports:
- 🇫🇷 French (fr)
- 🇬🇧 English (en)

Translations include:
- Person descriptions
- Question formulations
- Prompt templates
- Data (names, professions, colors)

## 🔧 Architecture

```
familybench/
├── tree_evaluator/
│   ├── models.py             # Person dataclass
│   ├── tree_generator.py     # Tree generation (+ actual_depth)
│   ├── text_converter.py     # Tree -> text description
│   ├── question_generator.py # Difficulty tiers, stratified sampling
│   ├── questions/            # One module per question family, enigma.py (9 levels), rewrite.py (anonymisation, counts)
│   ├── translations.py       # fr / en strings
│   ├── versioning.py         # Generator version + benchmark fingerprint
│   ├── cache_manager.py      # Optional diskcache of API responses
│   ├── visualizer.py         # Optional graphviz rendering
│   └── evaluation/
│       ├── model_evaluator.py  # API calls (OpenAI chat, OpenAI Responses, Anthropic), scoring
│       ├── runner.py           # Runs one benchmark for one model (concurrency, callbacks)
│       ├── answer_cleaner.py   # Answer normalisation
│       ├── stats.py            # Summary statistics
│       ├── display.py          # Rich progress UI
│       └── io.py               # CSV / JSON writers
├── data/{fr,en}/             # Names, professions, colours
├── tests/                    # pytest suite (generation, scoring, API parsing, end-to-end)
├── generate_benchmark.py     # CLI: generate a benchmark
├── evaluate.py               # CLI: evaluate models
└── analyze_results.py        # CLI: analyse results
```

## 📈 Performance

Typical generation times:
- 50 people, 100 questions: ~1 second
- 200 people, 500 questions: ~5 seconds
- 1000 people, 2000 questions: ~30 seconds

## 🏆 Benchmark Results

> **Reproducibility note.** The leaderboard below was produced in August-November 2025 with an earlier version of the generator and of the name lists. The name lists have since been extended and the question sampling made even across types, so `seed 43` no longer regenerates that exact tree. Runs are only comparable when they share the same `benchmark_fingerprint` (written in every summary since generator version 2.0). The 2025 table is kept as a historical reference; new runs should be compared against each other on the same fingerprint.

### Recent runs (2026, generator ≥ 2.0, not comparable with the 2025 table)

Benchmark `large_tree_en` (500 people, 4 root couples, depth 6, seed 1) unless stated otherwise.

| Model | Questions | Accuracy | Difficulty | Notes |
|---|---|---|---|---|
| Kimi K2.6 | 300 (3 runs × 100) | 81.7 % | all | 18 errors |
| DeepSeek V4 Flash | 200 | 80.5 % | expert | 83.8 % on enigmas, ~48k prompt tokens per question |
| Qwen 3.6 35B A3B (local) | 300 (3 runs × 100) | 79.3 % | all | |

Batch-size sweep, generator 3.1 (400 people, 4 root couples, depth 6, seed 43, `difficulty: expert`, 40 questions, DeepSeek V4 Flash 0731, unlimited reasoning):

| Batch size | Accuracy | Enigmas (levels 4-9) | Hard tier | Reasoning tokens / question | Prompt tokens | Cost |
|---|---|---|---|---|---|---|
| 1 | 85.0 % (3 network errors counted wrong) | 100 % | 74 % | 5,000 | 541k | $0.135 |
| 5 | 65.0 % | 71 % | 61 % | 3,000 | 118k | $0.051 |

Batching 5 questions per request divides the cost by 2.7 and costs 20 points, mostly on enigmas: the model reasons less per question and loses the chain. Batches of 20 on a 1,000-person tree never produced an answer within 160k reasoning tokens. Files in `evaluation_results/batch_sweep_deepseek/`.

Generator 4.0 (second unions, mixed-direction links, derived links, 2 children per union), same model, batch 1, 400 people, seed 2026, `difficulty: expert`, 40 questions, provider pinned (78 % of prompt tokens served from cache):

| | Generator 3.1 (seed 43) | Generator 4.0 (seed 2026) |
|---|---|---|
| Accuracy | 85.0 % | 50.0 % |
| Enigmas | 100 % | 78 % (3 of 4 misses are truncations) |
| Hard tier | 74 % | 27 % |
| Truncated at 160k output tokens | 0 | 7 |
| Reasoning tokens / question (avg) | 5,000 | 24,000 |
| Cost | $0.135 | $0.45 |

Protocol `hard-v4` (`evaluation_config_hard_v4.yaml`): hard tier only, 60 questions, batch 5, 16k output tokens per question, official DeepSeek API, entry `deepseek-v4-flash@high` (`thinking.reasoning_effort: high`):

| Entry | Accuracy | Truncated batches | Reasoning tokens / question | Cached prompt tokens | Cost | Wall time |
|---|---|---|---|---|---|---|
| deepseek-v4-flash@high | 48.3 % (29/60) | 1 of 12 | 13,100 | 62 % | $0.25 | 30 min |

Per type: conditional 78 %, half-siblings 75 %, step-parents 75 %, roots-with-criterion 50 %, descendants-with-criterion 50 %, multihop 22 %, comparative 0 %. The comparative questions ("who has the same number of children as X") are whole-tree censuses even when the answer is short, and no answer in 16k tokens is realistic; they are candidates for exclusion from the protocol. Files in `evaluation_results/hard_v4/`.

Files in `evaluation_results/v4_deepseek/`. The failure profile is recall on relatives (one name missing from a list, or "None" when the model does not find a link) and exhaustive comparisons ("who has the most children among X and their siblings") that exceed the token budget.

### Historical leaderboard (2025)

Here are the evaluation results of several state-of-the-art models on FamilyBench:

### Evaluation Configuration
- **Benchmark**: `huge_tree_en` - 400 people, requested depth 10 (5 generations actually reached), 200 questions requested, 10 root couples
- **Temperature**: 0.3 for all models
- **Evaluation Date**: August 14, 2025
- **Total Questions**: 189 per model (the enigma pool of that generator version only had 9 unique enigmas for the 20 requested, and nothing backfilled the difference; fixed since)

### Results Summary

| Model | Accuracy | Exact Match | Avg Response Time | Total Tokens | Reasoning Tokens | No Response Rate |
|-------|----------|-------------|-------------------|--------------|------------------|------------------|
| **Gemini 2.5 Pro** | **81.48%** | 77.25% | 22.54s | 271,500 | 95,260 | 0% |
| **Claude Sonnet 4.5** (New) | **77.78%** | 75.66% | 25.88s | 211,249 | 128,844 | 0% |
| **DeepSeek R1** | 75.66% | 74.07% | 97.83s | 430,628 | 575,624 | 0% |
| **GLM 4.6** (New) | **74.60%** | 72.49% | 89.11s | 245,113 | 305,120 | 0% |
| **Gemini 2.5 Flash** | 73.54% | 71.43% | 17.85s | 258,214 | 83,022 | 2.65% |
| **Qwen 3 Next 80B A3B Thinking** | 71.43% | 71.43% | 68.02s | 809,409 | 1,076,302 | 3.17% |
| **Claude Sonnet 4** | 67.20% | 65.08% | 32.93s | 258,883 | 150,642 | 1.06% |
| **DeepSeek V3.2 Exp** (New) | **66.67%** | 66.67% | 258.76s | 312,298 | 427,396 | 0% |
| **GLM 4.5** | 64.02% | 61.90% | 81.98s | 216,281 | 292,394 | 2.12% |
| **GLM 4.5 Air** | 57.14% | 56.61% | 268.11s | 909,228 | 1,270,138 | 26.46% |
| **GPT-OSS 120B** | 50.26% | 50.26% | 14.46s | 177,523 | 167,938 | 1.06% |
| **Qwen 3.2 Thinking** | 50.26% | 50.26% | 326.30s | 743,131 | 1,077,814 | 20.63% |
| **Kimi K2** | 34.92% | 34.92% | 16.04s | 67,071 | 0 | 0% |
| **Kimi K2 0905** (New) | **28.04%** | 28.04% | 9.35s | 7,684 | 0 | 0% |
| **Hunyuan A13B** | 30.16% | 30.16% | 91.52s | 131,672 | 121,150 | 2.12% |
| **GPT-OSS 20B** (New) | **30.16%** | 30.16% | 26.40s | 264,276 | 201,172 | 0% |
| **Mistral Medium 3.1** (New) | 29.63% | 29.63% | 6.64s | 6,062 | 0 | 0.53% |
| **Qwen 3.2** | 28.04% | 28.04% | 5.06s | 3,098 | 0 | 0.53% |
| **Mistral Small 3.2** | 22.22% | 22.22% | 13.03s | 5,353 | 0 | 0% |
| **Qwen 3 Coder** | 21.16% | 21.16% | 18.01s | 40,031 | 0 | 0% |
| **Gemma 3 27B** | 17.99% | 17.99% | 4.97s | 2,888 | 0 | 0.53% |
| **Qwen 3 30B A3B** | 7.94% | 7.94% | 6.74s | 7,096 | 0 | 0.53% |

### Detailed Performance Analysis

#### Top Performers

**Gemini 2.5 Pro** (Best Overall)
- **Accuracy**: 81.48% (154/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 84.44% (152/180 correct)
- **Efficiency**: Best accuracy with moderate token usage and fast responses
- **Reliability**: Perfect 0% no-response rate
- **Reasoning**: Efficient reasoning with only 504 tokens average

**Claude Sonnet 4.5** (Strong Second)
- **Accuracy**: 77.78% (147/189 correct)
- **Enigma Performance**: 33.33% (3/9 correct)
- **Normal Questions**: 80.00% (144/180 correct)
- **Speed**: Fast responses (25.88s average)
- **Efficiency**: Good balance with 682 avg reasoning tokens
- **Reliability**: Perfect 0% no-response rate and 0% error rate
- **Note**: Improved version of Sonnet 4, with better accuracy and enigma handling

**DeepSeek R1** (Top Tier)
- **Accuracy**: 75.66% (143/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 78.33% (141/180 correct)
- **Reasoning**: Moderate reasoning usage (3,078 avg tokens)
- **Reliability**: Excellent with 0% no-response rate
- **Note**: 1.06% error rate but still highly reliable

**GLM 4.6** (Impressive Improvement)
- **Accuracy**: 74.60% (141/189 correct)
- **Enigma Performance**: 44.44% (4/9 correct, **best enigma performance across all models**)
- **Normal Questions**: 76.11% (137/180 correct)
- **Response Time**: Moderate at 89.11s average
- **Reasoning**: Moderate reasoning usage (1,667 avg tokens, 183 questions with reasoning)
- **Reliability**: Perfect 0% no-response rate, 3.17% error rate
- **Note**: With improved prompting, GLM 4.6 jumped from 47.62% to 74.60% (+27 points!), showing excellent prompt sensitivity and reasoning capabilities

**Gemini 2.5 Flash**
- **Accuracy**: 73.54% (139/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 76.11% (137/180 correct)
- **Speed**: Fastest among top models (17.85s)
- **Efficiency**: Excellent balance - 73.54% accuracy with minimal reasoning tokens (439 avg)
- **Note**: Small 2.65% no-response rate but overall highly reliable

**Qwen 3 Next 80B A3B Thinking**
- **Accuracy**: 71.43% (135/189 correct)
- **Enigma Performance**: 33.33% (3/9 correct, tied for best enigma performance)
- **Normal Questions**: 73.33% (132/180 correct)
- **Reasoning**: Extensive reasoning usage (5,818 avg tokens)
- **Response Time**: Moderate at 68.02s average
- **Reliability**: Good with 3.17% no-response rate
- **Note**: Strong overall performance with particularly good enigma handling

**Claude Sonnet 4**
- **Accuracy**: 67.20% (127/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 69.44% (125/180 correct)
- **Efficiency**: Good balance of speed (32.93s) and accuracy
- **Reasoning**: Efficient with 797 avg reasoning tokens

**DeepSeek V3.2 Exp**
- **Accuracy**: 66.67% (126/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 68.89% (124/180 correct)
- **Response Time**: Slower at 258.76s average
- **Reasoning**: Moderate reasoning usage (2,559 avg tokens)
- **Reliability**: Perfect 0% no-response rate but 11.64% error rate
- **Note**: Experimental version with good accuracy but higher error rate

**GLM 4.5**
- **Accuracy**: 64.02% (121/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 66.11% (119/180 correct)
- **Balance**: Good accuracy with reasonable resource usage
- **Reliability**: Low 2.12% no-response rate

#### Mid-Tier Models

**GLM 4.5 Air**
- **Accuracy**: 57.14% (108/189 correct)
- **Enigma Performance**: 33.33% (3/9 correct, best enigma performance)
- **Token Usage**: 4.2x more tokens than standard GLM 4.5
- **Weakness**: Very high no-response rate (26.46%)

**GPT-OSS 120B** (New)
- **Accuracy**: 50.26% (95/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Normal Questions**: 52.22% (94/180 correct)
- **Speed**: Fast for its size (14.46s)
- **Reasoning**: Uses reasoning tokens extensively (1,200 avg)
- **Note**: A solid mid-tier performer, outperforming many similarly sized models.

**Qwen 3.2 Thinking**
- **Accuracy**: 50.26% (95/189 correct)
- **Enigma Performance**: 37.5% (3/8 correct, second best enigma)
- **Reasoning**: Extensive reasoning (7,185 avg tokens)
- **Weakness**: 20.63% no-response rate limits reliability

**Kimi K2**
- **Accuracy**: 34.92% (66/189 correct)
- **Speed**: Fast responses (16.04s average)
- **Enigma Performance**: 0% (failed all enigma questions)
- **Reliability**: Perfect 0% no-response rate

**Kimi K2 0905**
- **Accuracy**: 28.04% (53/189 correct)
- **Normal Questions**: 28.89% (52/180 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Speed**: Very fast responses (9.35s average)
- **Token Efficiency**: Extremely minimal (7,684 total, no reasoning tokens)
- **Reliability**: Perfect 0% no-response rate and 0% error rate
- **Note**: Lower accuracy than original Kimi K2 (34.92%) but faster and more efficient

**Hunyuan A13B**
- **Accuracy**: 30.16% (57/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Reasoning**: Light reasoning usage (641 avg tokens)
- **Response Time**: Slower at 91.52s average

**GPT-OSS 20B** (New)
- **Accuracy**: 30.16% (57/189 correct)
- **Enigma Performance**: 0% (0/9 correct)
- **Normal Questions**: 31.67% (57/180 correct)
- **Reliability**: Perfect 0% no-response rate
- **Reasoning**: High reasoning token usage for its performance level (2,211 avg)
- **Note**: Performance is in line with other models in its tier, but with higher token consumption.

**Mistral Medium 3.1** (New)
- **Accuracy**: 29.63% (56/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 30.00% (54/180 correct)
- **Speed**: Fast (6.64s average)
- **Token Efficiency**: Very low token usage (6,062 total)
- **Reliability**: 0.53% no-response rate
- **Reasoning**: No reasoning tokens used

#### Lower Performers

**Qwen 3.2** (Base Model)
- **Accuracy**: 28.04% (53/189 correct)
- **Speed**: Fastest model (5.06s average)
- **Token Efficiency**: Minimal token usage (3,098 total)
- **Enigma Performance**: 0% (failed all enigma questions)

**Mistral Small 3.2**
- **Accuracy**: 22.22% (42/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Speed**: Moderate (13.03s average)
- **Reliability**: Perfect 0% no-response rate

**Qwen 3 Coder**
- **Accuracy**: 21.16% (40/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Speed**: Moderate (18.01s average)
- **Token Usage**: Higher than similar performers (40,031 total)
- **Note**: Despite being a coding model, struggles with relational reasoning

**Gemma 3 27B**
- **Accuracy**: 17.99% (34/189 correct)
- **Speed**: Very fast (4.97s average)
- **Token Efficiency**: Extremely minimal (2,888 total)
- **Enigma Performance**: 0% (failed all enigma questions)

**Qwen 3 30B A3B** (Lowest Performer)
- **Accuracy**: 7.94% (15/189 correct)
- **Enigma Performance**: 0% (failed all enigma questions)
- **Speed**: Fast (6.74s average)
- **Token Efficiency**: Very minimal (7,096 total)
- **Note**: Waiting to test the thinking model !

### Key Insights

1. **Clear Top Tier**: Gemini 2.5 Pro (81.48%), Claude Sonnet 4.5 (77.78%), DeepSeek R1 (75.66%), GLM 4.6 (74.60%), Gemini 2.5 Flash (73.54%), and Qwen 3 Next 80B A3B Thinking (71.43%) form the elite group, all exceeding 70% accuracy
2. **Prompt Engineering Matters**: GLM 4.6 demonstrated a massive +27 point improvement (47.62% → 74.60%) with enhanced prompting, showing that prompt quality can dramatically impact model performance
3. **Claude Family Evolution**: Claude Sonnet 4.5 (77.78%) shows significant improvement over Sonnet 4 (67.20%), climbing to second place with better enigma handling (33.33% vs 22.22%)
4. **Enigma Excellence**: GLM 4.6 achieves the best enigma performance at 44.44% (4/9 correct), followed by Claude Sonnet 4.5 and Qwen 3 Next at 33.33%
5. **Qwen Generational Leap**: Qwen 3 Next 80B (71.43%) shows a +21.17 point improvement over Qwen 3.2 Thinking (50.26%), the biggest generational improvement observed
6. **Reasoning Capabilities Matter**: All top 6 models have reasoning capabilities, with DeepSeek V3.2 Exp (66.67%) and GLM 4.5 (64.02%) forming a strong second tier
7. **Gemini Family Dominance**: Both Gemini models (Pro and Flash) remain in the top tier, with Flash offering an excellent speed-accuracy balance
8. **DeepSeek Evolution**: DeepSeek V3.2 Exp (66.67%) shows competitive accuracy but with higher error rate (11.64%) compared to R1's perfect reliability
9. **Token Efficiency**: Gemini 2.5 Flash achieves 73.54% accuracy with only 439 reasoning tokens average, making it the most efficient top performer

### Benchmark Difficulty

The `huge_tree_en` benchmark represents an extreme challenge:
- **400 people** across 10 generations
- **10 root couples** creating multiple interconnected family trees
- **200 questions** testing various relationship types
- Models must maintain consistency across extremely long contexts
- **Enigma questions** require complex multi-step reasoning

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the project
2. Create a branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Ideas

- Add new languages
- Create new question types
- Improve generation algorithm
- Add tree visualizations
- Optimize performance

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by relational reasoning benchmarks
- Uses public domain name and profession data
- Designed for AI research and LLM evaluation

## 📧 Contact

For any questions or suggestions, feel free to open an issue on GitHub.

---

🤖 Made with ❤️ for LLM evaluation
