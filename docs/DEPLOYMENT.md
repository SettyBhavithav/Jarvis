# JARVIS V2 — Deployment & Operation Guide

## 1. Prerequisites
- **Operating System:** Windows 10/11 (64-bit)
- **Python:** Python 3.11.x (Installed at `C:\Users\setty\AppData\Local\Programs\Python\Python311\python.exe`)
- **Hardware:**
  - Minimum: 8 GB RAM, Quad-Core CPU, Working Microphone and Speakers.
  - Recommended: 16 GB RAM, NVIDIA GPU (for CUDA acceleration on Whisper STT).

---

## 2. Environment Configuration
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```
Key parameters:
```env
# AI Providers
GROQ_API_KEY=gsk_...
NIM_API_KEY=nvapi-...
DEEPSEEK_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# Supabase (Cloud Database & pgvector)
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=eyJhb...

# Discord Remote Bridge (Optional)
DISCORD_BOT_TOKEN=...
DISCORD_ALLOWED_USER_IDS=["123456789012345678"]
```
*Note: If `SUPABASE_URL` is omitted, JARVIS automatically initializes the embedded SQLite + Vector dual-engine storage layer with zero downtime.*

---

## 3. Launching JARVIS

### Voice Assistant Interactive Mode
```powershell
& "C:\Users\setty\AppData\Local\Programs\Python\Python311\python.exe" jarvis.py
```

### Headless FastAPI API Server
```powershell
& "C:\Users\setty\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```
Interactive OpenAPI documentation will be accessible at:
`http://127.0.0.1:8000/docs`

---

## 4. Supabase Database Migration
To apply the production PostgreSQL schema with `pgvector` and RLS policies:
1. Open your Supabase Dashboard SQL Editor.
2. Paste and run the contents of:
   `storage/migrations/001_initial_schema.sql`
3. All tables, vector indexes, and the `match_memories` RPC function will be provisioned.
