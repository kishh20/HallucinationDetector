# 🛡️ Hallucination Detector AI

> **Real-time web-grounded AI hallucination detection, fact-checking, and evidence verification with ChatGPT-grade UI.**

[![Live Web App](https://img.shields.io/badge/Live%20Demo-hallucinationdetector.onrender.com-10a37f?style=for-the-badge&logo=render)](https://hallucinationdetector.onrender.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%203.0-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![PWA Ready](https://img.shields.io/badge/Mobile-PWA%20Installable-blueviolet?style=for-the-badge&logo=pwa)](https://hallucinationdetector.onrender.com)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kishh20/HallucinationDetector)

---

## 🌟 Key Features

* **⚡ Real-Time Web Grounding & Parallel Retrieval**: Concurrently queries Wikipedia Live API, DuckDuckGo Knowledge, and Google News RSS to retrieve authoritative evidence before synthesizing claims.
* **🧠 Grounded Synthesis & Verification**: Powered by Google Gemini (`gemini-3.8-flash` / `gemini-flash-latest`), delivering high-speed, well-structured, factual answers backed by independent NLI verification.
* **🌊 Token-by-Token Streaming (Server-Sent Events)**: Streams responses live to the client as tokens are generated, updating evidence citations and attaching factual verification badges upon completion.
* **📐 KaTeX Math & Science Typesetting**: Built-in LaTeX equation rendering for inline (`$...$`, `\(...\)`) and display (`$$...$$`, `\[...\]`) formulas, with mobile-responsive horizontal scrolling.
* **🎙️ Voice Dictation (Speech-to-Text)**: Native browser Web Speech API dictation allows users to speak their questions hands-free directly into the search capsule.
* **📥 Export Verification Reports**: Export any verified conversation with a single click to **Markdown (`.md`)** (with claim audits and cited links) or structured **JSON (`.json`)**.
* **📱 Progressive Web App (PWA) Mobile Install**: Fully configured with Web App Manifest, Service Worker caching, and high-res app icons. Installable as a standalone full-screen app on **Android** (Chrome) and **iPhone** (iOS Safari).
* **🎨 ChatGPT-Inspired Matte Dark UI**: Sleek `#212121` palette with:
  * Interactive **Profile Popover Menu** (Settings `Ctrl+,`, Language, Help & FAQs, Plan Status, Apps, API Documentation, Admin Console, Sign Out).
  * 5-button action bar under answers (Copy with feedback, Read Aloud TTS, Thumbs Up, Thumbs Down with Diagnostic Auditor, and Regenerate).
  * Dynamic rotating suggestion cards across science, medicine, optics, history, and physics.
* **🔐 Persistent SQLite Sessions & Security**: Secure PBKDF2-HMAC password hashing (600,000 iterations), persistent SQLite session storage surviving server reboots, rate limiting, and GDPR-compliant account deletion.
* **🛡️ Admin Telemetry & Feedback Diagnostics**: Dedicated admin oversight panel for real-time visitor telemetry, login audits, user management, and automated root-cause diagnosis of user complaints with administrative approval workflows.

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

# Windows (PowerShell):
.\venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Set your Google Gemini API key:
```bash
# Windows (PowerShell):
$env:GEMINI_API_KEY = "your_gemini_api_key_here"

# Linux/macOS:
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### 5. Launch the application
```bash
python server.py
```
Open your browser at **`http://localhost:8000`** (or access the live cloud deployment at **`https://hallucinationdetector.onrender.com`**).

---

## 🏗️ Architecture

```
User Query (Text or Voice)
            │
            ▼
Parallel Search Engines (Wikipedia Live API + DuckDuckGo + Google News)
            │
            ├─────────────────────────────────────────────────┐
            ▼                                                 ▼
Grounded Stream Generator (Gemini 3.8 Flash)       Independent Verifier (NLI)
            │                                                 │
            ├────────────── SSE Stream ───────────────────────┤
            ▼                                                 ▼
Incremental Token Streaming (Markdown + KaTeX)     Faithful Evidence Confidence Badge
            │
            ▼
Interactive UI & Action Bar (Copy, TTS, Feedback, Report Export, PWA)
```

---

## 📁 Repository Structure

* `server.py`: FastAPI server managing SSE streaming (`/api/chat/stream`), authentication, SQLite sessions, conversation persistence, and admin analytics.
* `core_engine.py`: Parallel multi-source web search scraper, Gemini grounded answer generation & streaming, and NLI verification scoring.
* `auth_db.py`: SQLite database layer with PBKDF2 security, session persistence, login attempt rate-limiting, and visitor telemetry.
* `static/index.html`: Modern semantic HTML5 application layout with KaTeX math rendering, PWA metadata, modals, and voice inputs.
* `static/style.css`: Clean ChatGPT-grade matte dark theme (`#212121`), profile popover menu, mobile responsive layouts, and animations.
* `static/app.js`: Client-side logic for real-time SSE streaming, voice dictation, Markdown/KaTeX rendering, chat export, and Service Worker registration.
* `static/manifest.json`: Web App Manifest defining standalone PWA mobile application configuration.
* `static/sw.js`: Service Worker providing offline asset caching and fast mobile loading.
* `static/icons/`: High-resolution PWA icons (192x192, 512x512, maskable, and apple-touch-icon).
* `render.yaml`: Infrastructure-as-code configuration for Render automated cloud deployment.

---

## 📱 Mobile Installation (Android & iPhone)

1. Open **[https://hallucinationdetector.onrender.com](https://hallucinationdetector.onrender.com)** on your smartphone.
2. **Android**: Tap the **"📱"** icon in the header or Chrome menu (⋮) -> **"Install app"**.
3. **iPhone**: Tap **Share (⬆️)** in Safari -> **"Add to Home Screen (➕)"**.

---

## 📄 License

MIT License. Open-source for academic, educational, and developer use.
