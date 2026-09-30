# 🛡️ Hallucination Detector

> **Free web-grounded answers with independent verification**

A production-ready AI application that grounds user questions with real-time web retrieval, generates structured answers with citation tags, and performs multi-layer hallucination verification using an XGBoost model and independent NLI checks.

---

## 🌟 Features

- **🌐 Live Web Grounding**: Retrieves current context and real-time evidence for user queries using DuckDuckGo and Wikipedia scrapers.
- **🧠 Grounded Synthesis**: Generates accurate, cited responses powered by Google's Gemini models (`gemini-3-flash-preview` / `gemini-2.5-flash`).
- **🔍 Two-Stage Verification**:
  - **Sentence Deconstruction & Citation Verification**: Decomposes answers into individual factual claims and maps them back to retrieved evidence chunks.
  - **Machine Learning Verification (XGBoost V2)**: Evaluates semantic similarity, question-answer alignment, and lexical overlap to predict hallucination confidence scores.
- **🎨 Claude-Inspired UI**: Clean, warm dark-mode interface styled after Anthropic Claude and ChatGPT with interactive verification accordions, status badges, and source previews.
- **☁️ Production Ready**: Streamlit-based web frontend configured for custom domain deployment (e.g., Cloudflare Named Tunnels).

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/kishh20/HallucinationDetector.git
cd HallucinationDetector
```

### 2. Set up virtual environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Set your Gemini API key in your environment:
```bash
# Windows PowerShell:
$env:GEMINI_API_KEY = "your_gemini_api_key_here"

# Linux/macOS:
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### 5. Launch the application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🏗️ Architecture

```
User Query ──► Web Retrieval (Wikipedia / DuckDuckGo)
                     │
                     ▼
          Grounded Generator (Gemini)
                     │
                     ├───────────────┐
                     ▼               ▼
           Claim Decomposition   XGBoost V2 Classifier
                     │               │
                     └───────┬───────┘
                             ▼
                    Interactive UI Report
```

---

## 📁 Repository Structure

- `app.py`: Streamlit frontend with warm dark theme, chat UI, web grounding, and verification metrics.
- `pipeline.py`: Core ensemble verification (`verify_with_local_ml`) combining DeBERTa NLI and XGBoost V2.
- `generator.py`: Grounded generation module using Gemini API client.
- `verifier.py`: NLI DeBERTa-v3 cross-encoder claim verification.
- `hallucination_model_v2.pkl`: Pre-trained XGBoost V2 hallucination detection classifier.
- `predict.py`: Interactive CLI tool to test hallucination detection on custom inputs.
- `train_v2.py`: Model training script for XGBoost V2 classifier.
- `dataset.csv`: Labeled training dataset for model training and benchmarking.
- `cloudflare_tunnel_setup.md`: Guide for deploying with Cloudflare Named Tunnels.
- `requirements.txt`: Python package dependencies.
- `.streamlit/config.toml`: Custom theme styling and domain configuration.
