# Cloudflare Custom Domain Setup Guide: hallucinationdetector.com

This guide explains how to connect your production domain `https://hallucinationdetector.com` to the Hallucination Detector Streamlit application running on your server.

---

## 1. Prerequisites
1. You have registered the domain `hallucinationdetector.com` (on Cloudflare Registrar, Namecheap, GoDaddy, etc.).
2. The domain's nameservers are pointed to Cloudflare (Free plan is completely sufficient).
3. The application is running locally on port `8501`.

---

## 2. Setting Up Cloudflare Named Tunnel (Persistent Custom Domain)

While the temporary quick tunnel (`trycloudflare.com`) is useful for quick sharing, a production custom domain requires a **Cloudflare Named Tunnel**. This provides permanent, zero-downtime routing, automatic SSL/TLS certificates, and DDoS protection.

### Step A: Authenticate cloudflared
In your project directory, run:
```powershell
.\cloudflared.exe tunnel login
```
This opens your browser to log into your Cloudflare account and authorize the domain `hallucinationdetector.com`.

### Step B: Create a Named Tunnel
```powershell
.\cloudflared.exe tunnel create hallucination-detector
```
This creates a tunnel and outputs a Tunnel ID (e.g. `a1b2c3d4-e5f6-7890-abcd-ef0123456789`) and saves a credentials JSON file in `~/.cloudflared/`.

### Step C: Create the Tunnel Configuration File
Create a file named `config.yml` in `C:\Users\KISHOR SRE\.cloudflared\config.yml` (or in the project root):
```yaml
tunnel: <YOUR-TUNNEL-UUID>
credentials-file: C:\Users\KISHOR SRE\.cloudflared\<YOUR-TUNNEL-UUID>.json

ingress:
  # Route apex domain to Streamlit
  - hostname: hallucinationdetector.com
    service: http://localhost:8501

  # Route www subdomain to Streamlit
  - hostname: www.hallucinationdetector.com
    service: http://localhost:8501

  # Catch-all rule (required by Cloudflare Tunnel)
  - service: http_status:404
```

### Step D: Route the DNS Records
Run the following commands to create the CNAME DNS records automatically in your Cloudflare dashboard:
```powershell
.\cloudflared.exe tunnel route dns hallucination-detector hallucinationdetector.com
.\cloudflared.exe tunnel route dns hallucination-detector www.hallucinationdetector.com
```

### Step E: Run the Tunnel as a Background Service
To run the tunnel permanently:
```powershell
.\cloudflared.exe tunnel run hallucination-detector
```
Or install it as an automatic Windows system service:
```powershell
.\cloudflared.exe service install
Start-Service cloudflared
```

---

## 3. Streamlit Production Settings (Already Configured)

The application has already been configured with `.streamlit/config.toml`:
- `server.address = "0.0.0.0"`
- `server.port = 8501`
- `server.enableCORS = false`
- `server.enableXsrfProtection = false`
- `browser.serverAddress = "hallucinationdetector.com"`
- `browser.serverPort = 443`

---

## 4. Alternative: Deploying to Cloud Hosts (Streamlit Community Cloud / Render / Railway)

If you prefer to host 24/7 in the cloud without keeping your local machine on:
1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and deploy the repository.
3. In Streamlit Cloud settings, add your Custom Domain `hallucinationdetector.com`.
4. In Cloudflare DNS, add a CNAME record:
   - Type: `CNAME`
   - Name: `@`
   - Target: `<your-streamlit-app-url>.streamlit.app`
   - Proxy: `DNS only` (Grey cloud)
