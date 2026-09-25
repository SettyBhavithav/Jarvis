# JARVIS V2: Complete System Architecture Specification

---

## 1. High-Level Architectural Topology

JARVIS V2 is designed as an **Autonomous Multimodal AI Agent OS** operating on a hybrid edge-cloud paradigm:

```mermaid
flowchart TD
    %% Input Channels
    subgraph Inputs ["1. Input Gateway & Event Ingestion"]
        V[🎙️ Voice: 16kHz PyAudio]
        D[📱 Discord: OpenClaw Daemon]
        API[🌐 Internal REST API]
    end

    %% Central State & Event Bus
    subgraph Core ["2. Central State & Orchestration"]
        EB[⚡ Typed EventBus]
        RS[🧠 Runtime State Machine]
        CM[📜 Context Manager & SOUL]
    end

    Inputs --> EB
    Inputs --> RS
    Inputs --> CM

    %% Router & Intelligence Gateway
    subgraph Gateway ["3. Model Gateway & Health System"]
        IR[🧭 Intelligent Intent Router]
        CB[🚨 Circuit Breaker & Fallback]
        Groq[⚡ Groq LPU]
        NIM[👁️ NVIDIA NIM Vision & Gemma]
        DS[🔬 DeepSeek R1 Reasoning]
        Gemini[🌐 Google Gemini 2.0 Flash]
        Ollama[📴 Ollama Offline llama3.1:8b]
    end

    CM --> IR
    IR --> CB
    CB --> Groq & NIM & DS & Gemini & Ollama

    %% Security & Policy Engine
    subgraph Security ["4. Security & Policy Gatekeeper"]
        PE[🛡️ Policy Engine Levels 0-4]
        CMgr[✍️ Explicit Confirmation Manager]
        PID[🔒 Prompt Injection Context Isolator]
    end

    IR --> PE
    PE -->|Level 3 & 4 Actions| CMgr
    PE --> PID

    %% Tool Execution & Claw V2
    subgraph Tools ["5. Typed Tool Registry ('The Claw V2')"]
        TR[📦 Tool Registry]
        Diag[📊 System Diagnostics]
        Media[🎵 Spotify & Volume]
        Mail[📧 Background Gmail API]
        WA[💬 WhatsApp Desktop]
        Playwright[🕷️ Headless Web Scraper]
        Vis[👁️ Screen Vision]
        YT[📺 YouTube Transcript & Summary]
    end

    PE -->|Authorized| TR
    TR --> Diag & Media & Mail & WA & Playwright & Vis & YT

    %% Memory Layer
    subgraph Storage ["6. Persistence & Memory (Supabase pgvector)"]
        Supa[⚡ Supabase PostgreSQL]
        PGV[🧬 pgvector 384-dim Index]
        LocalCache[💾 SQLite Vector Fallback Cache]
        KG[🕸️ Knowledge Graph]
    end

    CM <--> Supa & PGV & LocalCache & KG

    %% Streaming Voice Output
    subgraph Output ["7. Streaming Voice Output & Barge-In"]
        SC[✂️ Sentence Chunker]
        TTS[🔊 Edge-TTS: en-US-GuyNeural]
        Mixer[🎧 Pygame Mixer Queue]
        Interrupt[🛑 0.8s Reverb Decay Barge-In]
    end

    Gateway --> SC --> TTS --> Mixer
    Mixer -.->|Echo Bleed| V
    V --> Interrupt --> Mixer
```

---

## 2. Architectural Subsystem Breakdown

### 2.1 Concurrency & Lifecycle
- **Wake Word Worker:** Runs continuous ONNX evaluation of `hey_jarvis` on background PyAudio frames at 16,000 Hz.
- **TTS Queue Worker:** AsyncIO loop consuming text chunks, calling Microsoft `edge-tts`, and piping audio streams directly to Pygame mixer.
- **Discord OpenClaw:** Background client checking message authors against `DISCORD_ALLOWED_USER_IDS` to prevent unauthorized remote PC control.
- **Main Agent Thread:** Manages speech acquisition, VAD filtering, orchestrator routing, and token streaming.

### 2.2 Memory Layer (Supabase pgvector + SQLite Offline Fallback)
- **Supabase PostgreSQL:** Stores structured tables (`users`, `sessions`, `messages`, `memories`, `tasks`, `audit_logs`).
- **384-Dimensional Dense Vectors:** Generated locally on CPU/GPU via `all-MiniLM-L6-v2`.
- **Hybrid Retrieval Algorithm:**
  $$\text{Final Score} = 0.70 \times \text{Cosine Similarity} + 0.30 \times \text{Importance}$$
- **Offline Cache:** When offline or missing cloud keys, operations execute transparently against SQLite with numpy vector search.

### 2.3 Security, Policy & Prompt-Injection Defense
- **Risk Level Hierarchy:**
  - **Level 0 (Conversational):** General chat, factual inquiries.
  - **Level 1 (Read-Only):** System stats, listing tasks/calendar events.
  - **Level 2 (Low-Risk Automation):** Launching apps, web searches, media playback toggle.
  - **Level 3 (Sensitive External Actions):** Sending emails, WhatsApp transfers, task deletion (**Requires Explicit User Confirmation**).
  - **Level 4 (Critical System Actions):** System shutdown, restart, workstation lock (**Requires Explicit User Confirmation**).
- **Context Isolation:** Untrusted web text and YouTube transcripts are enclosed in `<<<BEGIN_UNTRUSTED_EXTERNAL_DATA>>>` blocks to neutralize indirect prompt injection attacks.
