# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TreeEval is a French-language LLM evaluation tool that generates dynamic benchmarks to test relational reasoning capabilities. The project creates random family trees, converts them to textual descriptions, and generates question-answer pairs for evaluation.

## Core Architecture

The system follows a pipeline architecture:
1. **Tree Generation** (`tree_generator.py`): Creates random family trees with configurable constraints
2. **Text Conversion** (`text_converter.py`): Converts trees to structured French descriptions
3. **Question Generation** (`question_generator.py`): Generates 6 types of questions with answers
4. **CLI Scripts**: `generate_benchmark.py` (implemented), `evaluate.py` and `analyze_results.py` (placeholders)

Key data model in `models.py`:
- `Person` dataclass with unique constraints on names, professions, and color combinations
- Maintains parent-child relationships and generation levels

## Common Commands

### Generate a benchmark
```bash
# Basic usage
python generate_benchmark.py --people 30 --depth 3 --questions 50 --output benchmark.json

# Generate with Markdown output for direct LLM prompting
python generate_benchmark.py --people 5 --depth 2 --questions 10 --md-output prompt.md

# With custom seed for reproducibility
python generate_benchmark.py --people 50 --depth 4 --questions 100 --seed 12345 --output benchmark.json
```

**Note**: The tree generator may use fewer people than requested if:
- The depth is too high for the number of people (not enough to form couples in each generation)
- There's an imbalance of males/females preventing couple formation
- The algorithm stops early when no more couples can be formed

### Development Commands
```bash
# Run a specific file (no formal test framework exists yet)
python -m tree_evaluator.tree_generator
python -m tree_evaluator.text_converter
python -m tree_evaluator.question_generator

# Check imports and basic functionality
python -c "from tree_evaluator import *; print('Imports OK')"
```

## Important Constraints

When modifying the code, maintain these unique constraints:
- Each person must have a unique first name
- Each person must have a unique profession
- The combination (hair_color, eye_color, hat_color) must be unique
- Simple tree structure: no remarriages, each child has exactly 2 parents
- All output and documentation is in French

## Output Formats

The system generates two output formats:
1. **JSON**: Complete benchmark with metadata, questions, and answers
2. **Markdown**: LLM-ready prompt with instructions and questions (no answers)

Question types include: direct relations, inverse relations, attribute search, multi-criteria search, counting, and complex relations (siblings, grandparents).

## Current Implementation Status

✅ Implemented:
- Core tree generation with all constraints
- Text conversion with BFS ordering
- All 6 question types
- Benchmark generation (JSON and Markdown)

❌ Not implemented:
- Model evaluation (`evaluate.py`)
- Results analysis (`analyze_results.py`)
- External LLM integrations
- Formal testing framework
- Performance optimizations (pre-computed relations)