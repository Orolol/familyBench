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

FamilyBench generates 9 types of questions:

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

Here are the evaluation results of several state-of-the-art models on FamilyBench:

### Evaluation Configuration
- **Benchmark**: `huge_tree_en` - 400 people, depth 10, 200 questions, 10 root couples
- **Temperature**: 0.3 for all models
- **Evaluation Date**: July 28, 2025
- **Total Questions**: 189 per model (after filtering)

### Results Summary

| Model | Accuracy | Exact Match | Avg Response Time | Total Tokens | Reasoning Tokens | No Response Rate |
|-------|----------|-------------|-------------------|--------------|------------------|------------------|
| **Gemini 2.5 Pro** | **81.48%** | 77.25% | 22.54s | 271,500 | 95,260 | 0% |
| **DeepSeek R1** | 75.66% | 74.07% | 97.83s | 430,628 | 575,624 | 0% |
| **Gemini 2.5 Flash** | 73.54% | 71.43% | 17.85s | 258,214 | 83,022 | 2.65% |
| **Claude Sonnet 4** | 67.20% | 65.08% | 32.93s | 258,883 | 150,642 | 1.06% |
| **GLM 4.5** | 64.02% | 61.90% | 81.98s | 216,281 | 292,394 | 2.12% |
| **GLM 4.5 Air** | 57.14% | 56.61% | 268.11s | 909,228 | 1,270,138 | 26.46% |
| **Qwen 3.2 Thinking** | 50.26% | 50.26% | 326.30s | 743,131 | 1,077,814 | 20.63% |
| **Kimi K2** | 34.92% | 34.92% | 16.04s | 67,071 | 0 | 0% |
| **Horizon Alpha** | 33.33% | 33.33% | 5.34s | 17,512 | 0 | 0.53% |
| **Hunyuan A13B** | 30.16% | 30.16% | 91.52s | 131,672 | 121,150 | 2.12% |
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

**DeepSeek R1** (Strong Second)
- **Accuracy**: 75.66% (143/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 78.33% (141/180 correct)
- **Reasoning**: Moderate reasoning usage (3,078 avg tokens)
- **Reliability**: Excellent with 0% no-response rate
- **Note**: 1.06% error rate but still highly reliable

**Gemini 2.5 Flash** (New Addition)
- **Accuracy**: 73.54% (139/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 76.11% (137/180 correct)
- **Speed**: Fastest among top models (17.85s)
- **Efficiency**: Excellent balance - 73.54% accuracy with minimal reasoning tokens (439 avg)
- **Note**: Small 2.65% no-response rate but overall highly reliable

**Claude Sonnet 4**
- **Accuracy**: 67.20% (127/189 correct)
- **Enigma Performance**: 22.22% (2/9 correct)
- **Normal Questions**: 69.44% (125/180 correct)
- **Efficiency**: Good balance of speed (32.93s) and accuracy
- **Reasoning**: Efficient with 797 avg reasoning tokens

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

**Horizon Alpha** (New Addition)
- **Accuracy**: 33.33% (63/189 correct)
- **Enigma Performance**: 33.33% (3/9 correct, strong enigma performance)
- **Speed**: Very fast (5.34s average)
- **Token Efficiency**: Minimal usage (17,512 total)
- **Note**: Better at enigmas than normal questions

**Hunyuan A13B**
- **Accuracy**: 30.16% (57/189 correct)
- **Enigma Performance**: 11.11% (1/9 correct)
- **Reasoning**: Light reasoning usage (641 avg tokens)
- **Response Time**: Slower at 91.52s average

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

**Qwen 3 Coder** (New Addition)
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

**Qwen 3 30B A3B** (New Addition - Lowest Performer)
- **Accuracy**: 7.94% (15/189 correct)
- **Enigma Performance**: 0% (failed all enigma questions)
- **Speed**: Fast (6.74s average)
- **Token Efficiency**: Very minimal (7,096 total)
- **Note**: Waiting to test the thinking model !

### Key Insights

1. **Clear Top Tier**: Gemini 2.5 Pro (81.48%), DeepSeek R1 (75.66%), and Gemini 2.5 Flash (73.54%) significantly outperform all others
2. **Gemini Family Dominance**: Both Gemini models (Pro and Flash) are in the top 3, with Flash offering an excellent speed-accuracy balance
3. **Reasoning Capabilities Matter**: All top 5 models have reasoning capabilities, with Claude Sonnet 4 (67.20%) and GLM 4.5 (64.02%) forming a strong second tier
4. **Enigma Challenge**: All models struggle with enigma questions, with most achieving only 0-40% accuracy. Interestingly, Horizon Alpha (33.33%), GLM 4.5 Air, and Qwen Thinking perform better on enigmas despite lower overall scores
5. **Reliability vs Performance**: High no-response rates (GLM 4.5 Air: 26.46%, Qwen Thinking: 20.63%) make these models impractical despite decent accuracy
6. **Speed-Accuracy Trade-off**: The fastest models (Gemma 3: 4.97s, Qwen 3.2: 5.06s, Horizon Alpha: 5.34s) have lower accuracy, though Gemini 2.5 Flash breaks this pattern with fast speed and high accuracy
7. **Token Efficiency**: Gemini 2.5 Flash achieves 73.54% accuracy with only 439 reasoning tokens average, making it the most efficient top performer

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