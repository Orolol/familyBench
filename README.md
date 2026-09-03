# FamilyBench 🌳

FamilyBench is a dynamic benchmark for the relational reasoning of large language models. It generates a random family tree, writes it out as a long, deliberately inconvenient textual description, and asks questions whose answers are fully determined by that text: who is the half-sister of the person with auburn hair, amber eyes and a burgundy hat, which descendants of X work as a pilot, who has the most children among Y and their siblings. Every benchmark is regenerated from a seed, so nothing can leak into training data, and every answer is verified programmatically.

The current protocol, **hard-v4**, is described below with its leaderboard. Earlier protocols and their results are kept at the end for reference.

## 🏆 Leaderboard — protocol hard-v4 (2026-09-03)

| # | Entry | Accuracy | Truncated questions | Output tokens / question | Output tokens / correct answer | Cached prompt | Cost (100 q) | Served by |
|---|---|---|---|---|---|---|---|---|
| 1 | `gpt-5.6@high` | **90%** | 0 | 1,217 | 1,352 | 0% | $3.66 | OpenAI Responses API |
| 2 | `claude-opus-5@high` | **89%** | 0 | 1,756 | 1,973 | 79% | $5.07 | Anthropic Messages API |
| 3 | `qwen3.8-max@budget16k` | **88%** | 0 | 6,873 | 7,810 | 85% | $3.54 | Alibaba DashScope |
| 4 | `gemini-3.8-flash@high` | **87%** | 0 | 7,881 | 9,059 | 4% | $3.19 | OpenRouter (Google AI Studio) |
| 5 | `deepseek-v4-pro@high` | **81%** | 0 | 7,190 | 8,877 | 88% | $2.91 | DeepSeek API |
| 6 | `claude-fable-5.1@high` | **80%** | 0 | 951 | 1,189 | 79% | $5.85 | Anthropic Messages API |
| 7 | `muse-spark-1.3-contributor@high` | **79%** | 0 | 2,453 | 3,105 | 10% | $0.08 | OpenRouter (Meta) |
| 8 | `kimi-k3@high` | **75%** | 0 | 2,482 | 3,309 | 25% | $4.45 | Moonshot API |
| 9 | `glm-5.3@high` | **64%** | 5 | 3,378 | 5,278 | 64% | $1.70 | Z.ai API |
| 10 | `gpt-5.6-terra@high` | **62%** | 0 | 866 | 1,397 | 0% | $1.65 | OpenAI Responses API |
| 11 | `gpt-5.6-luna@high` | **58%** | 0 | 2,763 | 4,764 | 0% | $0.39 | OpenAI Responses API |
| 12 | `glm-5.3-flash@high` | **43%** | 10 | 3,302 | 7,680 | 0% | $0.21 | Z.ai API |

**How to read it.** An entry is a *(model, thinking level)* pair: thinking effort is not comparable across vendors and the benchmark does not pretend it is, so the level is part of the name and is reported as such. Each entry ran once on the same 100 questions (seed 4040), in 20 batches of 5, with a hard cap of **16,000 output tokens per question** (80k per request, reasoning included). Differences under about 7 points are within run-to-run noise (measured on two identical DeepSeek passes: 39 of 60 questions kept their verdict). *Output tokens / correct answer* is the efficiency ranking: the same accuracy costs GPT-5.6 six times fewer tokens than Qwen 3.8 Max or Gemini 3.8 Flash. Costs use the vendors' list prices of 2026-09-03; the whole pass cost $33.

Per question type (correct / total):

| Entry | step-parents | half-siblings | conditional | descendants + criterion | roots + criterion | multihop |
|---|---|---|---|---|---|---|
| `gpt-5.6@high` | 17/17 | 14/16 | 15/17 | 17/17 | 14/16 | 13/17 |
| `claude-opus-5@high` | 17/17 | 16/16 | 17/17 | 14/17 | 16/16 | 9/17 |
| `qwen3.8-max@budget16k` | 17/17 | 16/16 | 13/17 | 16/17 | 14/16 | 12/17 |
| `gemini-3.8-flash@high` | 16/17 | 16/16 | 12/17 | 17/17 | 15/16 | 11/17 |
| `deepseek-v4-pro@high` | 17/17 | 13/16 | 13/17 | 14/17 | 14/16 | 10/17 |
| `claude-fable-5.1@high` | 17/17 | 16/16 | 11/17 | 16/17 | 10/16 | 10/17 |
| `muse-spark-1.3-contributor@high` | 16/17 | 16/16 | 14/17 | 15/17 | 8/16 | 10/17 |
| `kimi-k3@high` | 17/17 | 15/16 | 13/17 | 11/17 | 10/16 | 9/17 |
| `glm-5.3@high` | 16/17 | 9/16 | 12/17 | 8/17 | 12/16 | 7/17 |
| `gpt-5.6-terra@high` | 15/17 | 10/16 | 13/17 | 10/17 | 7/16 | 7/17 |
| `gpt-5.6-luna@high` | 15/17 | 8/16 | 10/17 | 9/17 | 7/16 | 9/17 |
| `glm-5.3-flash@high` | 10/17 | 8/16 | 8/17 | 8/17 | 4/16 | 5/17 |

**What the pass showed.**
- The top four (GPT-5.6, Claude Opus 5, Qwen 3.8 Max, Gemini 3.8 Flash) sit within 3 points, below the noise floor; separating them needs a second seed. They reach that score with very different budgets: 1,200 to 1,800 output tokens per question for the OpenAI and Anthropic models, 7,000 to 8,000 for Qwen, Gemini and DeepSeek Pro.
- The 16k cap only bit GLM-5.3 (5 truncated questions) and GLM-5.3-Flash (10). Nobody else came close, so the capped pass is the reference and an uncapped "max effort" pass would only change the GLM rows.
- The discriminating question types are **multihop** ("the children of the siblings of the grandparents of X") and **roots with criterion** ("people without parents who work as X"), both of which require scanning the whole description. The relation types added by generator 4.0 (step-parents, half-siblings) are solved by every model above 75 %.
- Muse Spark 1.3 at 79 % for $0.08 is by far the best score per dollar; Claude Fable 5.1 trails Claude Opus 5 by 9 points while using half the tokens, mostly on conditional questions ("who has the most children among X and their siblings").

Files: `evaluation_results/hard_v4/` (`summary_*.json` per entry, `results_*.json/csv` per question, `detailed_*.json` with the exact prompt; `_orphan_partials/` holds incremental files of processes that were restarted, and the DeepSeek Pro entry was rebuilt from the response cache so its response times are zero there).

## 🧬 What the benchmark is (generator 4.0)

### The tree

- Random family trees with unique first names and unique (hair, eyes, hat) combinations; professions repeat on purpose so that "who works as a pilot" has several answers.
- Each child has exactly two parents. A configurable share of people (`second_union_percentage`, default 20 %) also have children with a second partner, which creates **half-siblings and step-parents**. "Brother/sister" means both parents in common, "half-brother/half-sister" exactly one; uncles, cousins and nephews are defined through full siblings. This convention is written at the top of every description.
- Two children per union by default (`max_children`), so 400 people give about 6 generations. The requested depth is an upper bound: the pool of people is usually exhausted before it is reached, and the actual depth is recorded in every output.

### The description

- Every parent-child link is stated **exactly once, in a random direction and place** (`relations: mixed`): "Ana is the mother of Leo" here, "Leo is the son of Marc" forty lines later. Knowing both parents of someone means joining two distant sentences.
- A share of people (`derived_links_percentage`, default 30 %) are described only as "X is the sister of Y"; Y keeps explicit links and is never derived itself, so the tree stays fully reconstructible (a test rebuilds it from the sentences).
- Sentences are shuffled with a generator seeded from the benchmark seed: the sorted order leaked everyone's generation, and the seeding keeps the description byte-identical across runs so provider prompt caches keep hitting.
- About 13,000 tokens for 400 people.

### The questions

23 question types in four difficulty tiers (`easy`, `medium`, `hard`, `enigma`), sampled evenly across types. The `hard` tier used by the protocol: conditional, multihop, descendants with criterion, roots with criterion, half-siblings, step-parents (plus compound attributes, relational paths, comparatives and negations, which the protocol excludes, see below). Enigmas are relation chains with a unique discriminating attribute ("Which grandfather of the aunt of the grandfather of Lacey has blue eyes?"), in nine complexity levels; they turned out to be solved at 100 % by mid-tier models once the phrasing was made unambiguous, which is why the protocol focuses on the hard tier instead.

Two rewrites apply after sampling: in `anonymize_percentage` (default 50 %) of the questions every first name is replaced by the person's unique attribute description ("the person with red hair, blue eyes and a green hat"), so the model must locate the person before reasoning; and questions whose answer would list more than `max_answer_names` (10) names are asked as counts, while those above `drop_answer_names_above` (40) are dropped as whole-tree censuses. Answers are a single name, an alphabetically sorted comma-separated list, a number, or `None`.

Every generated question records `type`, `difficulty`, `answer_format` (`names`, `count`, `label`, `none`), `anonymized` and `converted_to_count`.

### Difficulty levers

All levers are `generate_benchmark.py` flags and `benchmarks:` keys of the evaluation config, and all are part of the benchmark fingerprint. Defaults are the hard settings.

| Lever | Key | Default | Effect |
|---|---|---|---|
| Second unions | `second_union_percentage` | 20 | Half-siblings and step-parents; `0` restores the single-union tree |
| Children per union | `max_children` | 2 | Fewer children per union means more generations for the same tree size |
| Link phrasing | `relations` | `mixed` | `mixed` (each link once, random direction), `parents`, `children`, `both` (redundant, easiest) |
| Derived links | `derived_links_percentage` | 30 | "X is the sister of Y" instead of X's parent links |
| Shuffle | `shuffle` | true | Seeded shuffle of the sentences |
| Attribute references | `anonymize_percentage` | 50 | Names replaced by attribute descriptions in the questions (never in enigmas) |
| Long answers as counts | `max_answer_names` | 10 | Above N names the question becomes "how many people…" |
| Census questions dropped | `drop_answer_names_above` | 40 | Above N names the question is removed before sampling |
| Excluded types | `exclude_types` | none | e.g. `[relational_path, relation_attribut_composee, comparative, negation]` |

```bash
# Easier description, single unions, no rewrites (close to the 2025 protocol)
python generate_benchmark.py --people 400 --depth 6 --questions 200 --seed 43 --language en \
    --no-shuffle --relations both --max-children 3 --second-union-percentage 0 --derived-links-percentage 0 \
    --max-answer-names 0 --anonymize-percentage 0 --output easy.json
```

### Reproducibility

Every benchmark carries a fingerprint (`benchmark_fingerprint`, in the generated JSON and in every summary) computed from the generator version, the data files (name lists) and all generation parameters. Two runs are comparable only if their fingerprints match. Question selection is reproducible across processes and machines for a given seed (the generator never iterates over sets).

## 📐 Protocol hard-v4

`evaluation_config_hard_v4.yaml` is the reference configuration:

| Parameter | Value | Why |
|---|---|---|
| Tree | 400 people, 4 root couples, seed 4040, generator 4.0 defaults | About 13k prompt tokens; 6 generations |
| Questions | 100, `difficulty: hard`, evenly spread over 6 types | Enigmas and the easier tiers are saturated by current models |
| Excluded types | relational paths, compound attributes, comparatives, negations | The first two are the easiest hard types; the last two are whole-tree censuses ("who has the same number of children as X") that no model answers within budget |
| Batch | 5 questions per request | Halves the cost and is itself part of the difficulty: on generator 3.1, batch 5 cost DeepSeek V4 Flash 20 points |
| Output cap | `max_tokens_per_question: 16000`, i.e. 80,000 per request | Reasoning and answer included; a truncated request loses its 5 questions ("cannot answer within budget") and is not retried |
| Effort | `high` on every vendor (`budget16k` on Qwen, see below) | The common label; levels are not equivalent and are displayed as such |
| Temperature | vendor default | Anthropic rejects it with thinking, reasoning models ignore it, Moonshot fixes it |
| Robustness | streaming everywhere, idle timeout 300 s, retries on stalled streams, connection resets, HTTP 429/5xx (backoff, `retry-after`) | Truncated generations are never retried nor cached |

Vendor notes learned on the first pass: Moonshot allows **one concurrent request per organisation** (run Kimi with `--max-concurrent 1`, patient retries are set in the config); Qwen's `max_tokens` does not cover the chain of thought, so the Qwen entry sets `thinking_budget` (16k × batch) instead of an effort level, hence `@budget16k`; DeepSeek expects the effort inside `thinking.reasoning_effort` (`effort_param: thinking`); identity-linked Anthropic keys need `anthropic_workspace_id`; OpenAI's prompt cache reported writes but no reads during the pass, so OpenAI costs are without cache discount.

### Running the protocol

```bash
# 1. Cost check: same protocol on 2 questions per entry (entries without an API key are skipped)
python evaluate.py --config evaluation_config_hard_v4_smoke.yaml
python scripts/estimate_cost.py evaluation_results/hard_v4_smoke/summary_<ts>.json --questions 100

# 2. The pass: one process per entry, in parallel (entries inside one process run sequentially)
python evaluate.py --config evaluation_config_hard_v4.yaml --models claude-opus-5@high
python evaluate.py --config evaluation_config_hard_v4.yaml --models kimi-k3@high --max-concurrent 1
...
```

Each run writes `partial_<ts>.jsonl` incrementally (nothing is lost if a process dies), then `results_<ts>.csv/json`, `detailed_<ts>.json` (prompts and every Q&A) and `summary_<ts>.json` (per-entry stats, per-type and per-tier accuracy, hallucination rate, fingerprint, entry metadata). Responses are cached on disk (`.cache/`, `diskcache`) keyed by the full request, so an interrupted entry can be relaunched and only pays for what it has not completed. Keys are read from `.env` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID`, `DEEPSEEK_API_KEY`, `QWEN_API_KEY`, `MOONSHOT_API_KEY`, `ZAI_API_KEY`, `OPENROUTER_API_KEY`).

## 📊 Scoring

The model answer is normalised (JSON objects or arrays, numbered lists, `<answer>` tags, "Final answer:" prefixes, spelled-out numbers, `None`/`Aucun` variants) and both sides are compared as sets, case-insensitively, after the same normalisation:

| Metric | Definition |
|---|---|
| `is_exact_match` | Same set of names (order ignored) |
| `partial_match_score` | Jaccard index between the two sets |
| `is_correct` | Exact match **or** Jaccard ≥ 0.9; since long answers are asked as counts, this only ever tolerates one name on lists of 10 |
| `no_response` | Empty answer, refusal, truncation, or a sentence instead of an answer |
| `hallucinated_names` | Names in the answer that do not exist in the tree (only when the expected answer is a list of names) |

`accuracy` is the share of `is_correct` over all questions, errors and no-responses included. In batch mode the model answers with a JSON object keyed by question number, so a skipped question does not shift the others. `scripts/rescore_results.py` re-scores existing files after a scoring change.

## ⚙️ Configuration reference

Per-entry keys of `models:`:

| Key | Meaning |
|---|---|
| `name` | Leaderboard entry, by convention `model@level` |
| `api` | `anthropic` (Messages API), `openai_responses`, or `openai_chat` (any OpenAI-compatible endpoint: OpenAI chat, OpenRouter, DeepSeek, Qwen, Moonshot, Z.ai, Gemini compat, local servers). Auto-detected from `api_base` when omitted |
| `effort` | Generic effort label, translated into `output_config.effort` (Anthropic, adaptive thinking), `reasoning.effort` (OpenAI Responses), `reasoning_effort` (OpenAI-compatible), `reasoning: {effort}` (OpenRouter) |
| `effort_param` | For OpenAI-compatible vendors: `reasoning_effort` (default), `thinking` (DeepSeek), `none` |
| `budget_param` | Name of a thinking-budget parameter set to `max_tokens_per_question` × batch size (Qwen: `thinking_budget`) |
| `thinking_level` | Label shown in the leaderboard (defaults to `effort`) |
| `max_tokens_per_question` | Output cap per question; the request cap is this times the batch size. `0` falls back to `max_tokens` |
| `extra_body` | Vendor-specific parameters merged into the request (`thinking: {type: enabled}`, `enable_thinking`, Gemini's `google.thinking_config`…) |
| `reasoning`, `provider` | OpenRouter-style reasoning object and provider routing (`order`, `allow_fallbacks`) — pin a provider: prompt caches are per provider |
| `pricing` | `input_per_mtok`, `output_per_mtok`, `cached_input_per_mtok` to get `cost_usd` |
| `anthropic_workspace_id` | Required with identity-linked Anthropic keys |
| `stream`, `idle_timeout`, `http_retries`, `http_retry_max_wait`, `request_delay_ms` | Streaming (default on), stall cut-off, HTTP retry policy, pacing |

Per-benchmark keys of `benchmarks:`: `people`, `depth`, `questions`, `root_couples`, `seed`, `language` (`fr`/`en`), `difficulty` (`all`, `easy`, `medium`, `hard`, `enigma`, `expert`), `enigma_percentage`, `exclude_types`, and the difficulty levers above. `evaluation:` keys: `runs_per_benchmark`, `max_concurrent_requests`, `timeout`, `batch_size`, `output_dir`, `output_formats`. Command-line overrides: `--models`, `--benchmarks`, `--batch-size`, `--runs`, `--max-concurrent`, `--output-dir`, `--debug`.

## 🚀 Installation and other tools

```bash
pip install -r requirements.txt      # aiohttp, pyyaml, python-dotenv, rich, diskcache; pandas/matplotlib for the analysis
pytest                               # 114 tests, no network needed (fake API servers)

# Generate a benchmark file (JSON with answers, optional Markdown prompt)
python generate_benchmark.py --people 400 --depth 8 --questions 100 --root-couples 4 --seed 4040 --language en --difficulty hard --output bench.json

# Analyse results (per model, per type, per tier, plots, HTML report)
python analyze_results.py evaluation_results/hard_v4/results_*.csv --plots
python analyze_results.py evaluation_results/**/results_*.csv --exclude-failed-runs

# Compare batch sizes on one model (accuracy vs cost)
python scripts/batch_sweep.py --config evaluation_config_batch_sweep.yaml --batch-sizes 1 5 10 20
```

Repository layout:

```
tree_evaluator/
├── tree_generator.py, text_converter.py      # tree and description (generator 4.0)
├── question_generator.py, questions/         # 23 question types, tiers, enigma chain engine, rewrites
├── versioning.py                             # generator version and benchmark fingerprint
└── evaluation/                               # API adapters (Anthropic, OpenAI Responses, OpenAI-compatible),
                                              # streaming, scoring, stats, rich display, I/O
scripts/                                      # batch_sweep.py, estimate_cost.py, rescore_results.py
evaluation_config_hard_v4*.yaml               # the protocol and its 2-question smoke variant
evaluation_results/                           # every run, incremental and final files
tests/                                        # pytest suite
```

## 📜 History

### 2026, generators 2.0 to 4.0 (not comparable with each other nor with the leaderboard)

- **Generator 2.0**, `large_tree_en` (500 people, seed 1), batch 1, unlimited reasoning: Kimi K2.6 81.7 %, DeepSeek V4 Flash 80.5 % (expert), Qwen 3.6 35B A3B (local) 79.3 %.
- **Generator 3.1 batch-size sweep**, DeepSeek V4 Flash, 400 people, expert, 40 questions: batch 1 85.0 %, batch 5 65.0 %. Batching divides the cost by 2.7 and costs 20 points, mostly on enigmas. Batches of 20 on a 1,000-person tree never produced an answer within 160k reasoning tokens.
- **Generator 4.0 versus 3.1**, same model, batch 1, expert, 40 questions: 85 % → 50 %; hard tier 74 % → 27 %; reasoning per question 5k → 24k tokens; 7 questions truncated at 160k output tokens. The failure profile is recall (one name missing, or "None" when a link is missed) and exhaustive comparisons that exceed the budget.
- **Pre-protocol tests**, DeepSeek V4 Flash on the official API, hard tier, 60 questions, batch 5: `@high` with the 16k cap 48.3 %, `@max` uncapped 53.3 %; the two passes agreed on only 39 of 60 questions, which is the origin of the ±7 points noise estimate. Comparative questions scored 0/9 in both and were excluded from the protocol.

Files: `evaluation_results/batch_sweep_deepseek/`, `evaluation_results/v4_deepseek/`, `evaluation_results/hard_v4_deepseek_flash_tests/`, `evaluation_results/hard_v4_smoke*/`.

### 2025 leaderboard (generator 1.x, historical)

Benchmark `huge_tree_en` (400 people, requested depth 10 with 5 generations actually reached, 189 questions, 10 root couples), temperature 0.3, reasoning capped at 8,000 tokens, batch 1, via OpenRouter. The name lists and the question sampling have changed since, so `seed 43` no longer regenerates this benchmark; the table is kept as a reference. The per-model commentary of that era is available in the git history.

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

1. **Clear Top Tier**: Gemini 2.5 Pro (81.48%), Claude Sonnet 4.5 (77.78%), DeepSeek R1 (75.66%), GLM 4.6 (74.60%), Gemini 2.5 Flash (73.54%), and Qwen 3 Next 80B A3B Thinking (71.43%) form the elite group, all exceeding 70% accuracy
2. **Prompt Engineering Matters**: GLM 4.6 demonstrated a massive +27 point improvement (47.62% → 74.60%) with enhanced prompting, showing that prompt quality can dramatically impact model performance
3. **Claude Family Evolution**: Claude Sonnet 4.5 (77.78%) shows significant improvement over Sonnet 4 (67.20%), climbing to second place with better enigma handling (33.33% vs 22.22%)
4. **Enigma Excellence**: GLM 4.6 achieves the best enigma performance at 44.44% (4/9 correct), followed by Claude Sonnet 4.5 and Qwen 3 Next at 33.33%
5. **Qwen Generational Leap**: Qwen 3 Next 80B (71.43%) shows a +21.17 point improvement over Qwen 3.2 Thinking (50.26%), the biggest generational improvement observed
6. **Reasoning Capabilities Matter**: All top 6 models have reasoning capabilities, with DeepSeek V3.2 Exp (66.67%) and GLM 4.5 (64.02%) forming a strong second tier
7. **Gemini Family Dominance**: Both Gemini models (Pro and Flash) remain in the top tier, with Flash offering an excellent speed-accuracy balance
8. **DeepSeek Evolution**: DeepSeek V3.2 Exp (66.67%) shows competitive accuracy but with higher error rate (11.64%) compared to R1's perfect reliability
9. **Token Efficiency**: Gemini 2.5 Flash achieves 73.54% accuracy with only 439 reasoning tokens average, making it the most efficient top performer

## 🤝 Contributing

Contributions are welcome: new languages, new question families (bounded aggregation over a branch is the next difficulty lever we would add), vendor adapters, analysis. Open an issue or a pull request.

## 📝 License

MIT — see [LICENSE](LICENSE).
