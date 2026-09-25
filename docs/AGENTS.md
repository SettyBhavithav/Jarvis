# JARVIS V2 — Autonomous Multi-Agent OS Architecture

## 1. Overview
JARVIS V2 implements a specialized multi-agent operating architecture where each agent is an autonomous, domain-focused intelligence coordinated by the core `AgentPlanner` and `Orchestrator`.

```
                  ┌─────────────────────────────────┐
                  │    User (Voice / Discord / API) │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │  Model Router & Safety Policy   │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │  Central Orchestrator & Planner │
                  └──────┬─────────┬─────────┬──────┘
                         │         │         │
       ┌─────────────────┼─────────┼─────────┼─────────────────┐
       ▼                 ▼         ▼         ▼                 ▼
┌──────────────┐  ┌──────────┐ ┌───────┐ ┌────────┐     ┌──────────────┐
│ Conversation │  │ Coding / │ │ Email │ │Browser │ ... │   Computer   │
│    Agent     │  │ Research │ │ Agent │ │ Agent  │     │    Agent     │
└──────────────┘  └──────────┘ └───────┘ └────────┘     └──────────────┘
```

---

## 2. Specialized Agent Directory

### 1. ConversationAgent (`agents/conversation_agent.py`)
- **Role:** Fast-path dialogue, personality management, and conversational queries.
- **Provider:** Groq (Llama-3.3-70b-versatile) / Gemini 2.0 Flash / Ollama fallback.
- **Latency Target:** Sub-second (< 600ms).

### 2. CodingAgent (`agents/conversation_agent.py`)
- **Role:** Full-stack software engineering, architecture, code reviews, and debugging.
- **Provider:** DeepSeek V3 / NVIDIA Qwen 2.5 Coder.

### 3. ResearchAgent (`agents/conversation_agent.py`)
- **Role:** Deep factual research, scientific logic, mathematical reasoning, and source synthesis.
- **Provider:** DeepSeek R1 / NVIDIA Llama 3.1 70B Thinking Mode.

### 4. VisionAgent (`agents/conversation_agent.py`)
- **Role:** Real-time visual analysis of the user's primary monitor, OCR, UI element inspection, and debugging error screens.
- **Provider:** NVIDIA NIM Vision / Gemini 2.0 Flash.

### 5. DocumentAgent (`agents/document_agent.py`)
- **Role:** Semantic RAG over local PDFs, markdown documentation, and text files using vector similarity.
- **Engine:** Ingestion and chunking engine backed by `sentence-transformers/all-MiniLM-L6-v2`.

### 6. EmailAgent (`agents/email_agent.py`)
- **Role:** Gmail inbox querying, thread reading, draft generation, and sending with Level 3 confirmation gating.

### 7. CalendarAgent (`agents/calendar_agent.py`)
- **Role:** Google Calendar agenda inspection, event creation, conflict checks, and schedule summaries.

### 8. TaskAgent (`agents/task_agent.py`)
- **Role:** Action item management, persistent to-do lists, priority queues, and task status transitions.

### 9. BrowserAgent (`agents/browser_agent.py`)
- **Role:** Live internet browsing, headless web scraping, Playwright DOM parsing, and webpage summarization.

### 10. ComputerAgent (`agents/computer_agent.py`)
- **Role:** Native Windows automation: CPU/RAM/Battery metrics, window activation, media controls, and desktop file discovery.

### 11. DiscordAgent (`agents/discord_agent.py`)
- **Role:** Autonomous bridge between Discord channels and the central orchestrator with default-deny allowlist security.
