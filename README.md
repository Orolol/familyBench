# TreeEval 🌳

TreeEval is an evaluation tool for testing the relational reasoning capabilities of Large Language Models (LLMs). It generates random family trees, converts them to textual descriptions, and creates question-answer pairs to evaluate understanding of complex family relationships.

## 🎯 Objective

TreeEval enables systematic and reproducible evaluation of LLMs' ability to:
- Understand direct family relationships (parents, children)
- Infer complex relationships (grandparents, cousins, uncles/aunts)
- Reason across multiple generations
- Combine relationships with attributes (profession, physical appearance)
- Perform cross-sectional and vertical queries in the family tree

## 🌟 Features

- **Dynamic generation**: Creation of random family trees with configurable constraints
- **Multi-language**: Support for French and English
- **Varied question types**: 9 categories of questions with increasing difficulty
- **Automatic evaluation**: Interface with OpenAI-compatible APIs to test multiple models
- **Reproducibility**: Use of seeds to generate identical benchmarks
- **Flexible export**: JSON and Markdown formats for direct LLM integration

## 📋 Prerequisites

- Python 3.8+
- pip

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/treeeval.git
cd treeeval
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
```

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
    
  - name: "small_en"
    people: 30
    depth: 3
    questions: 50
    language: "en"
    seed: 42
```

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
```

### Results Analysis

```bash
# Analyze evaluation results
python analyze_results.py evaluation_results/results_*.csv

# Generate comparative plots
python analyze_results.py evaluation_results/results_*.csv --plots

# Export detailed report
python analyze_results.py evaluation_results/results_*.csv --report report.html
```

## 🧠 Question Types

TreeEval generates 9 types of questions:

1. **Direct relations**: "Who are Marie's children?"
2. **Inverse relations**: "Whose child is Jean?"
3. **Attribute search**: "Who has blonde hair?"
4. **Multi-criteria search**: "Who has brown hair and blue eyes?"
5. **Counting**: "How many children does Pierre have?"
6. **Complex relations**: "Who are Sophie's cousins?"
7. **Cross-sectional questions**: "Who is in the same generation as Luc and works as a doctor?"
8. **Vertical questions**: "Who are Claire's oldest ancestors?"
9. **Compound relations**: "Which of Paul's children work as engineers?"

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
    "language": "en",
    "generation_timestamp": "2024-01-15T10:30:00"
  }
}
```

### Generation Constraints

- **Name uniqueness**: Each person has a unique first name
- **Profession uniqueness**: Each person has a unique profession
- **Appearance uniqueness**: The combination (hair, eyes, hat) is unique
- **Simple structure**: No remarriages, each child has exactly 2 parents

## 🌍 Multi-language Support

TreeEval currently supports:
- 🇫🇷 French (fr)
- 🇬🇧 English (en)

Translations include:
- Person descriptions
- Question formulations
- Prompt templates
- Data (names, professions, colors)

## 🔧 Architecture

```
treeeval/
├── tree_evaluator/
│   ├── __init__.py
│   ├── models.py           # Data models (Person)
│   ├── tree_generator.py   # Tree generation
│   ├── text_converter.py   # Text conversion
│   ├── question_generator.py # Question generation
│   └── translations.py     # Translation system
├── data/
│   ├── fr/                # French data
│   └── en/                # English data
├── generate_benchmark.py   # CLI for generation
├── evaluate.py            # Model evaluation
└── analyze_results.py     # Results analysis
```

## 📈 Performance

Typical generation times:
- 50 people, 100 questions: ~1 second
- 200 people, 500 questions: ~5 seconds
- 1000 people, 2000 questions: ~30 seconds

## 🏆 Benchmark Results

Here are the evaluation results of several state-of-the-art models on TreeEval:

### Evaluation Configuration
- **Benchmarks**: 
  - `large_tree_en`: 100 people, depth 4, 100 questions
  - `huge_tree_en`: 200 people, depth 8, 100 questions
- **Runs**: 3 runs per benchmark (600 questions total per model)
- **Temperature**: 0.3 for all models

### Results by Model

| Model | Global Accuracy | Large Tree | Huge Tree | Avg Time | Tokens Used |
|-------|-----------------|------------|-----------|----------|-------------|
| **Gemini 2.5 Pro** | **70.17%** | 78.33% | 62.00% | 9.22s | 1,238,391 |
| **Kimi K2** | 45.00% | 52.67% | 37.33% | 5.08s | 3,907 |
| **o4-mini-high** | 42.83% | 53.67% | 32.00% | 29.81s | 645,714 |
| **Mistral Small 3.2** | 41.67% | 45.67% | 37.67% | 5.73s | 13,314 |
| **Claude Opus 4** | 30.33% | 34.33% | 26.33% | 9.62s | 2,691 |
| **DeepSeek R1** | 27.67% | 32.00% | 23.33% | 41.47s | 329,004 |
| **Qwen 3.2** | 22.33% | 25.33% | 19.33% | 43.58s | 200,866 |
| **GLM 4.1v** | 7.33% | 11.00% | 3.67% | 35.14s | 293,232 |
| **Magistral Medium** | 0.00% | 0.00% | 0.00% | 3.92s | 0 |

### Results Analysis

- **Best model**: Gemini 2.5 Pro dominates with 70% accuracy, particularly strong on medium-sized trees
- **Efficiency**: Kimi K2 offers the best speed/performance tradeoff (45% accuracy in 5s)
- **Scalability**: All models see performance drop on very deep trees (huge_tree)
- **Variability**: Some models show high variability between runs (e.g., Claude Opus 4)

### Observed Challenges

Models particularly struggle with:
- Complex relationships (cousins, uncles/aunts) in large trees
- Cross-sectional questions requiring traversal of multiple generations
- Maintaining consistency over very long descriptions (200+ people)

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