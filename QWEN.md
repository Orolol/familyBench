# FamilyBench Project Context for Qwen Code

## Project Overview

FamilyBench is a Python-based evaluation tool designed to test the relational reasoning capabilities of Large Language Models (LLMs). It achieves this by:

1.  **Generating Random Family Trees:** Creates complex family structures with configurable parameters (number of people, generations, root couples).
2.  **Converting to Text:** Transforms the generated family tree into a detailed textual description.
3.  **Creating Questions:** Formulates a diverse set of questions (9 distinct types) based on the family tree to probe the model's understanding of relationships, attributes, and complex reasoning.
4.  **Evaluating Models:** Provides a framework to automatically evaluate LLMs via API calls using the generated benchmarks.
5.  **Analyzing Results:** Offers tools to analyze the performance of different models.

The project is structured to be language-agnostic (currently supporting French and English) and focuses on reproducibility through the use of seeds.

**Key Technologies:**

*   **Language:** Python 3.8+
*   **Dependencies:** `aiohttp`, `pyyaml`, `python-dotenv`, `pandas`, `matplotlib`, `seaborn`. (See `requirements.txt`)

## Project Structure

Based on the `README.md` architecture diagram and directory listing:

```
familybench/
├── tree_evaluator/
│   ├── __init__.py
│   ├── models.py           # Data models (e.g., Person)
│   ├── tree_generator.py   # Core logic for generating family trees
│   ├── text_converter.py   # Converts tree data to human-readable text
│   ├── question_generator.py # Coordinates generation of various question types
│   └── translations.py     # Handles multi-language support
│   └── questions/          # Subdirectory containing modules for each question type
├── data/
│   ├── fr/                # French data (names, professions, colors)
│   └── en/                # English data
├── generate_benchmark.py   # CLI tool for creating benchmarks (JSON/Markdown)
├── evaluate.py             # Main CLI tool for running model evaluations
├── analyze_results.py      # CLI tool for analyzing evaluation results
├── evaluation_config.yaml  # Default configuration for evaluations
└── ... (other config, docs, output dirs)
```

## Core Functionalities

### 1. Benchmark Generation (`generate_benchmark.py`)

This script is the entry point for creating a new FamilyBench benchmark.

*   **Purpose:** Generate a family tree, convert it to text, create questions, and output the benchmark in JSON or Markdown format ready for LLM consumption.
*   **Key Parameters:**
    *   `--people`: Total number of individuals in the tree.
    *   `--depth`: Maximum number of generations.
    *   `--questions`: Number of questions to generate.
    *   `--language`: Target language ('fr' or 'en').
    *   `--seed`: Ensures reproducibility.
    *   `--root-couples`: Number of initial family units.
    *   `--max-children`: Limits children per person.
    *   `--output`: Saves benchmark in JSON format.
    *   `--md-output`: Saves benchmark in Markdown format, pre-formatted for direct LLM prompting (with JSON response instructions).

### 2. Model Evaluation (`evaluate.py`, `evaluation_config.yaml`)

This script automates the process of sending benchmarks to LLMs via API and collecting their responses.

*   **Purpose:** Run configured benchmarks against specified LLMs and record their answers for analysis.
*   **Configuration (`evaluation_config.yaml`):**
    *   `models`: List of models to evaluate, including API endpoint, key, model name, and parameters (e.g., temperature).
    *   `benchmarks`: List of benchmark configurations to run (people, depth, questions, seed, language).
    *   `evaluation`: Settings like number of runs, timeouts, batch sizes, and output formats (CSV, JSON).
*   **Execution:** `python evaluate.py [--config custom_config.yaml] [--models model1 model2] [--benchmarks bench1 bench2]`

### 3. Results Analysis (`analyze_results.py`)

This script processes the output files from the evaluation phase.

*   **Purpose:** Calculate metrics (accuracy, exact match, response time), generate comparative reports and plots.
*   **Execution:** `python analyze_results.py evaluation_results/results_*.csv [--plots] [--report report.html]`

## Development Conventions

*   **Modular Design:** The `tree_evaluator` package is well-organized, separating concerns (models, generation, conversion, questions).
*   **Question Types:** New question types are implemented in dedicated modules within `tree_evaluator/questions/` and integrated via `question_generator.py`.
*   **Multi-language:** Language-specific data and translations are managed in the `data/` directory and `tree_evaluator/translations.py`.
*   **Data Model:** The `Person` dataclass in `tree_evaluator/models.py` centralizes individual attributes and relationships.
*   **CLI Tools:** The project provides three main command-line interfaces for generation, evaluation, and analysis, making it user-friendly.

## Building and Running

*   **Prerequisites:** Python 3.8+, `pip`.
*   **Installation:**
    1.  Clone the repository.
    2.  Run `pip install -r requirements.txt`.
    3.  (Optional) Create a `.env` file with API keys (e.g., `OPENROUTER_API_KEY`).
*   **Usage (from project root):**
    *   **Generate Benchmark:**
        ```bash
        # JSON output
        python generate_benchmark.py --people 50 --depth 4 --questions 100 --language en --output benchmark_en.json
        # Markdown output for direct prompting
        python generate_benchmark.py --people 20 --depth 3 --questions 30 --md-output prompt.md
        ```
    *   **Run Evaluation:**
        ```bash
        # Evaluate all models/benchmarks in default config
        python evaluate.py
        # Evaluate specific models
        python evaluate.py --models gpt-3.5-turbo claude-3
        # Use a custom config
        python evaluate.py --config my_eval_config.yaml
        ```
    *   **Analyze Results:**
        ```bash
        # Analyze results
        python analyze_results.py evaluation_results/results_*.csv
        # Generate plots
        python analyze_results.py evaluation_results/results_*.csv --plots
        # Export detailed report
        python analyze_results.py evaluation_results/results_*.csv --report report.html
        ```
*   **Testing:** `pytest` is listed as a dependency, suggesting tests might exist or are planned, though not explicitly detailed in the provided files.

## Question Types

The benchmark generates 9 main categories of questions, increasing in complexity:

1.  Direct relations
2.  Inverse relations
3.  Attribute search
4.  Multi-criteria search
5.  Counting
6.  Complex relations (e.g., cousins)
7.  Cross-sectional questions
8.  Vertical questions (ancestors/descendants)
9.  Compound relations

There is also an "enigma" type for particularly challenging multi-step reasoning.

## Data Constraints

*   Unique first names.
*   Unique combinations of hair color, eye color, and hat color for individuals.
*   Simple family structure (no remarriages, exactly two parents per child).
