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
- **Benchmark**: `huge_tree_en` - 400 people, depth 10, 200 questions, 10 root couples
- **Temperature**: 0.3 for all models
- **Evaluation Date**: July 28, 2025
- **Total Questions**: 189 per model (after filtering)

### Results Summary

| Model | Accuracy | Exact Match | Avg Response Time | Total Tokens | Reasoning Tokens | No Response Rate |
|-------|----------|-------------|-------------------|--------------|------------------|------------------|
| **Gemini 2.5 Pro** | **81.48%** | 77.25% | 22.54s | 271,500 | 95,260 | 0% |
| **GLM 4.5** | 64.02% | 61.90% | 81.98s | 216,281 | 292,394 | 2.12% |
| **GLM 4.5 Air** | 57.14% | 56.61% | 268.11s | 909,228 | 1,270,138 | 26.46% |
| **Qwen 3.2 Thinking** | 50.26% | 50.26% | 326.30s | 743,131 | 1,077,814 | 20.63% |
| **Kimi K2** | 34.92% | 34.92% | 16.04s | 67,071 | 0 | 0% |
| **Qwen 3.2** | 28.04% | 28.04% | 5.06s | 3,098 | 0 | 0.53% |
| **Mistral Small 3.2** | 22.22% | 22.22% | 13.03s | 5,353 | 0 | 0% |

### Detailed Performance Analysis

#### Top Performers

**Gemini 2.5 Pro** (Best Overall)
- **Accuracy**: 81.48% (154/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 84.44% (152/180 correct)
- **Efficiency**: Best accuracy with moderate token usage and fast responses
- **Reliability**: Perfect 0% no-response rate
- **Reasoning**: Efficient reasoning with only 504 tokens average

**GLM 4.5**
- **Accuracy**: 64.02% (121/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 66.11% (119/180 correct)
- **Balance**: Good accuracy with reasonable resource usage
- **Reliability**: Low 2.12% no-response rate

**GLM 4.5 Air**
- **Accuracy**: 57.14% (108/189 correct)
- **Enigma Performance**: 33.33% (3/9 correct, best enigma performance)
- **Token Usage**: 4.2x more tokens than standard GLM 4.5
- **Weakness**: Very high no-response rate (26.46%)

**Qwen 3.2 Thinking**
- **Accuracy**: 50.26% (95/189 correct)
- **Enigma Performance**: 37.5% (3/8 correct, second best)
- **Reasoning**: Extensive reasoning (7,185 avg tokens)
- **Weakness**: 20.63% no-response rate limits reliability

#### Mid-Tier Models

**Kimi K2**
- **Accuracy**: 34.92% (66/189 correct)
- **Speed**: Fast responses (16.04s average)
- **Enigma Performance**: 0% (failed all enigma questions)
- **Reliability**: 100% response rate

**Qwen 3.2** (Base Model)
- **Accuracy**: 28.04% (53/189 correct)
- **Speed**: Fastest model (5.06s average)
- **Token Efficiency**: Minimal token usage (3,098 total)
- **Enigma Performance**: 0% (failed all enigma questions)

#### Lower Performers

**Mistral Small 3.2**
- **Accuracy**: 22.22% (42/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Speed**: Moderate (13.03s average)
- **Reliability**: Perfect 0% no-response rate


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