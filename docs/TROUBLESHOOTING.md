# JARVIS V2 — Troubleshooting & Diagnostics Guide

## 1. Diagnostic Matrix

| Issue | Root Cause | Resolution |
|---|---|---|
| `UnicodeEncodeError: 'charmap' codec can't encode character` | Windows console defaults to legacy `cp1252` encoding. | Handled automatically in entry points via `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`. If running standalone scripts, set `PYTHONIOENCODING=utf-8`. |
| `ImportError: cannot import name 'xxx' from 'huggingface_hub'` | Version conflict between older `huggingface_hub` and newer `transformers`. | Upgraded to `huggingface_hub>=1.32.0`. |
| `Tool execution timeout` | Third-party service or network hang. | Handled gracefully by `ToolRegistry` timeout isolation (default 30s). The planner initiates self-correction. |
| `Discord bot not responding` | User ID is not listed in `DISCORD_ALLOWED_USER_IDS`. | Add your numeric Discord User ID to `.env`. Remember that an empty list defaults strictly to DENY. |
| `Supabase connection timeout` | Network firewall or missing Supabase URL. | JARVIS automatically switches to the offline SQLite vector engine with zero interruptions. |

---

## 2. Audio & Microphone Diagnostics
If wake-word detection is not triggering:
1. Verify Windows microphone permissions in Windows Settings -> Privacy & Security -> Microphone.
2. Check available audio input devices:
   ```python
   import sounddevice as sd
   print(sd.query_devices())
   ```
3. If background noise is high, adjust `WAKE_WORD_THRESHOLD=0.25` in `.env`.

---

## 3. Provider Health Check & Circuit Breakers
To inspect live status of all upstream LLM providers:
```powershell
& "C:\Users\setty\AppData\Local\Programs\Python\Python311\python.exe" -c "from models.health import provider_health; print(provider_health.get_all_health())"
```
Or query the API:
`GET /api/health`
