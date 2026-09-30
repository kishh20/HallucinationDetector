# 🚀 Deploying Hallucination Detector to Render with Custom Domain

This guide walks you through deploying **Hallucination Detector** to [Render](https://render.com) and linking your custom domain **`https://hallucinationdetector.com`**.

---

## ⚡ Option 1: 1-Click Blueprint Deploy (Fastest)

Click the button below to deploy automatically via the included `render.yaml` blueprint:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kishh20/HallucinationDetector)

1. Sign in to your [Render](https://dashboard.render.com) account.
2. Select your repository: `kishh20/HallucinationDetector`.
3. Enter your environment variables:
   - `GEMINI_API_KEY`: Your Gemini API key.
   - `OPENROUTER_API_KEY` (Optional): If using OpenRouter models.
4. Click **Apply**. Render will automatically build and deploy the web service.

---

## 🛠️ Option 2: Manual Web Service Setup

If you prefer to configure the service manually in the Render dashboard:

1. Go to [Render Dashboard](https://dashboard.render.com) and click **New +** > **Web Service**.
2. Connect your GitHub account and choose **`kishh20/HallucinationDetector`**.
3. Configure the service settings:
   - **Name**: `hallucination-detector`
   - **Region**: Oregon (US West) or Frankfurt (EU)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
     ```
4. Scroll down to **Environment Variables** and add:
   - `PYTHON_VERSION`: `3.11.8`
   - `GEMINI_API_KEY`: *(Your key)*
   - `OPENROUTER_API_KEY`: *(Your key, optional)*
5. Click **Create Web Service**.

---

## 🌐 Linking Custom Domain: `hallucinationdetector.com`

Once your service is created:

### Step 1: Add Custom Domains in Render
1. In your Render service page, navigate to **Settings** > **Custom Domains**.
2. Click **Add Custom Domain** and enter:
   - `hallucinationdetector.com`
3. Click **Add Custom Domain** again and enter:
   - `www.hallucinationdetector.com`

---

### Step 2: Configure DNS Records at Your Registrar
Open your DNS provider dashboard (e.g., Cloudflare, Namecheap, GoDaddy, Google Domains) for `hallucinationdetector.com` and add the following records:

| Type | Name / Host | Target / Value | TTL | Note |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `@` (root) | `216.24.57.1` | Auto / 3600 | Render's Anycast IP |
| **CNAME** | `www` | `hallucination-detector.onrender.com` | Auto / 3600 | Points www to your service |

> **Tip for Cloudflare Users:**
> If your domain is managed on Cloudflare:
> - Set Proxy status to **DNS only** (gray cloud) during initial verification so Render can issue the SSL certificate.
> - Or use CNAME flattening for the root domain (`@` -> `hallucination-detector.onrender.com`).

---

### Step 3: Automatic SSL Verification
- Render will automatically verify the DNS records and issue a free **Let's Encrypt TLS/SSL certificate**.
- All HTTP traffic is automatically redirected to **`https://hallucinationdetector.com`**.
