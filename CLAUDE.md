# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TreeEval is a multi-language LLM evaluation tool that generates dynamic benchmarks to test relational reasoning capabilities. The project creates random family trees, converts them to textual descriptions, and generates question-answer pairs for evaluation. Supports French (fr) and English (en).

## Core Architecture

The system follows a pipeline architecture:
1. **Tree Generation** (`tree_generator.py`): Creates random family trees with configurable constraints
2. **Text Conversion** (`text_converter.py`): Converts trees to structured descriptions (French/English)
3. **Question Generation** (`question_generator.py`): Generates 9 types of questions with answers
4. **Model Evaluation** (`evaluate.py`): Async evaluation system for testing LLMs via OpenAI-compatible APIs
5. **CLI Scripts**: `generate_benchmark.py`, `evaluate.py`, `analyze_results.py` (placeholder)

Key modules:
- `models.py`: Core `Person` dataclass with unique constraints
- `translations.py`: Multi-language support system
- `evaluation/`: Complete async evaluation framework with answer cleaning, stats, and result formatting
- `questions/`: Modular question generation system with 9 question types including enigmas

## Common Commands

### Generate a benchmark
```bash
# Basic usage (French)
python generate_benchmark.py --people 30 --depth 3 --questions 50 --output benchmark.json

# English benchmark
python generate_benchmark.py --people 50 --depth 4 --questions 100 --language en --output benchmark_en.json

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
```

### Development Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Format code (if black is installed)
black tree_evaluator/ *.py

# Type checking (if mypy is installed)
mypy tree_evaluator/

# Run tests (if pytest is installed)
pytest
```

## Important Constraints

When modifying the code, maintain these unique constraints:
- Each person must have a unique first name
- Each person must have a unique profession
- The combination (hair_color, eye_color, hat_color) must be unique
- Simple tree structure: no remarriages, each child has exactly 2 parents
- Support both French and English throughout the codebase

## Output Formats

The system generates multiple output formats:
1. **JSON Benchmark**: Complete benchmark with metadata, questions, and answers
2. **Markdown Prompt**: LLM-ready prompt with instructions and questions (no answers)
3. **CSV Results**: Evaluation results with detailed metrics per question
4. **JSON Results**: Complete evaluation data including reasoning tokens and response times

## Question Types

The system generates 9 types of questions:
1. **Direct relations**: "Who are Marie's children?"
2. **Inverse relations**: "Whose child is Jean?"
3. **Attribute search**: "Who has blonde hair?"
4. **Multi-criteria search**: "Who has brown hair and blue eyes?"
5. **Counting**: "How many children does Pierre have?"
6. **Complex relations**: "Who are Sophie's cousins?"
7. **Cross-sectional**: "Who is in the same generation as Luc and works as a doctor?"
8. **Vertical**: "Who are Claire's oldest ancestors?"
9. **Enigmas**: Complex riddles requiring multi-step reasoning

## Evaluation System

The evaluation framework (`tree_evaluator/evaluation/`) includes:
- **Async API calls** with configurable timeout and retries
- **Answer cleaning** to normalize LLM responses (handles JSON arrays, numbered lists, etc.)
- **Detailed metrics**: accuracy, exact match, partial match, response time, token usage
- **Reasoning token tracking** for models that support it (o1, deepseek-r1)
- **Batch processing** support for efficiency
- **Multiple output formats**: CSV and JSON with full details

## Current Implementation Status

✅ Fully Implemented:
- Core tree generation with all constraints
- Text conversion with BFS ordering
- All 9 question types including enigmas
- Benchmark generation (JSON and Markdown)
- Complete async evaluation system
- Multi-language support (French/English)
- Answer cleaning and normalization
- Detailed statistics and metrics

❌ Not implemented:
- Results analysis visualization (`analyze_results.py`)
- Formal unit testing framework
- Performance optimizations (pre-computed relations)
- Additional languages beyond French/English