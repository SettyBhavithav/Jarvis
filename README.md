%%{init: {'theme': 'dark'}}%%
flowchart TD

    classDef inputStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef audioStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#ffffff;
    classDef secStyle fill:#311b05,stroke:#f59e0b,stroke-width:2px,color:#ffffff;
    classDef agentStyle fill:#2e1065,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef modelStyle fill:#172554,stroke:#60a5fa,stroke-width:2px,color:#ffffff;
    classDef toolStyle fill:#042f2e,stroke:#2dd4bf,stroke-width:2px,color:#ffffff;
    classDef storeStyle fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef outStyle fill:#431407,stroke:#fb923c,stroke-width:2px,color:#ffffff;

    subgraph T1 ["1. SENSORY INGESTION"]
        IN_MIC["Microphone (16kHz PyAudio)"]:::inputStyle
        IN_DISCORD["Discord OpenClaw Gateway"]:::inputStyle
        IN_CLI["Terminal CLI / REST API"]:::inputStyle
        IN_SCREEN["Screen Capture (PyAutoGUI)"]:::inputStyle
    end

    subgraph T2 ["2. AUDIO PROCESSING & STT"]
        OWW["openwakeword (hey_jarvis @ 0.15)"]:::audioStyle
        VAD["Dynamic Normalization & VAD"]:::audioStyle
        STT_GROQ["Groq LPU (whisper-large-v3-turbo)"]:::audioStyle
        STT_LOCAL["Local faster-whisper Fallback"]:::audioStyle
    end

    IN_MIC --> OWW
    OWW -->|Wake Detected| VAD
    VAD --> STT_GROQ
    VAD -.->|Offline| STT_LOCAL

    subgraph T3 ["3. SECURITY & RISK POLICY"]
        AUTH_GATE["GoTrue Bearer JWT Auth"]:::secStyle
        POLICY["Risk Policy Engine (Levels 0-4)"]:::secStyle
        INJECT["Context Delimiter Wrapper"]:::secStyle
        CONFIRM["Interactive Confirmation Gate"]:::secStyle
    end

    IN_DISCORD --> AUTH_GATE
    IN_CLI --> AUTH_GATE
    STT_GROQ --> AUTH_GATE
    STT_LOCAL --> AUTH_GATE
    IN_SCREEN --> AUTH_GATE

    AUTH_GATE --> POLICY
    POLICY -->|Level 0-2: Read-Only| INJECT
    POLICY -->|Level 3-4: Destructive| CONFIRM
    CONFIRM -->|User Approved| INJECT

    subgraph T4 ["4. AUTONOMOUS REACT AGENT"]
        PLANNER["Goal Planner & Sub-Task Tracker"]:::agentStyle
        ROUTER["Capability & Complexity Router"]:::agentStyle
        RECOVERY["Goal-Preserving Error Recovery"]:::agentStyle
    end

    INJECT --> PLANNER
    PLANNER --> ROUTER
    RECOVERY --> PLANNER

    subgraph T5 ["5. NEURAL MODEL GATEWAY"]
        M_GROQ["Primary Fast Chat: Groq LPU (Qwen 3.8 27B)"]:::modelStyle
        M_NIM["Vision & Reasoning: NVIDIA NIM (Llama 3.2 11B)"]:::modelStyle
        M_DEEPSEEK["Code & Logic: DeepSeek (Coder / Reasoner)"]:::modelStyle
        M_GEMINI["Multimodal Fallback: Google Gemini (2.0 Flash)"]:::modelStyle
        M_OLLAMA["Zero-Internet Fallback: Ollama (llama3.1:8b)"]:::modelStyle
    end

    ROUTER -->|Chat & General| M_GROQ
    ROUTER -->|Vision Intent| M_NIM
    ROUTER -->|Code & Complex Math| M_DEEPSEEK
    M_GROQ -.->|Rate Limit / Timeout| M_NIM
    M_NIM -.->|Fallback| M_GEMINI
    M_DEEPSEEK -.->|Fallback| M_NIM
    M_GROQ & M_NIM & M_DEEPSEEK -.->|Offline| M_OLLAMA

    subgraph T6 ["6. TYPED TOOL REGISTRY (THE CLAW)"]
        T_SYS["System Diagnostics (psutil)"]:::toolStyle
        T_WEB["Web Automation (Playwright Headless)"]:::toolStyle
        T_MAIL["Google Workspace (Gmail & Calendar)"]:::toolStyle
        T_MEDIA["Windows Media Hooks & Spotify"]:::toolStyle
        T_WA["WhatsApp Desktop Automation"]:::toolStyle
        T_YT["YouTube Transcript & Summarizer"]:::toolStyle
    end

    M_GROQ -->|Tool Call| T_SYS & T_WEB
    M_DEEPSEEK -->|Tool Call| T_MAIL & T_WA
    M_NIM -->|Tool Call| T_MEDIA & T_YT
    M_OLLAMA -->|Tool Call| T_SYS
    T_SYS & T_WEB & T_MAIL & T_MEDIA & T_WA & T_YT -.->|Failure| RECOVERY

    subgraph T7 ["7. STORAGE & PERSISTENCE"]
        SUPA_AUTH["Supabase PostgreSQL (Row-Level Security)"]:::storeStyle
        SUPA_VEC["pgvector Memory (384-dim all-MiniLM-L6-v2)"]:::storeStyle
        SUPA_SCHED["Atomic Task Scheduler (status='claimed')"]:::storeStyle
        SUPA_AUDIT["Append-Only Security Audit Trail"]:::storeStyle
        SQLITE_CACHE["Local SQLite Offline Resilience Cache"]:::storeStyle
    end

    PLANNER <-->|RAG Memory Recall| SUPA_VEC
    PLANNER <-->|Persistent Tasks| SUPA_SCHED
    T_SYS & T_WEB & T_MAIL & T_MEDIA & T_WA & T_YT -->|Audit Log| SUPA_AUDIT
    SUPA_AUTH --> SUPA_VEC & SUPA_SCHED & SUPA_AUDIT
    SUPA_VEC & SUPA_SCHED -.->|Sync Queue| SQLITE_CACHE

    subgraph T8 ["8. STREAMING VOICE OUTPUT"]
        CHUNK["Natural Sentence Chunker (. ! ?)"]:::outStyle
        TTS["Edge-TTS Streaming Engine (en-US-GuyNeural)"]:::outStyle
        MIXER["Pygame Asynchronous Audio Mixer Buffer"]:::outStyle
        BARGE_IN["Hardware Barge-In Interruption & 0.8s Decay"]:::outStyle
        SPEAKERS["Physical Laptop Speakers"]:::outStyle
    end

    PLANNER -->|Speech Tokens| CHUNK
    CHUNK --> TTS
    TTS --> MIXER
    MIXER --> SPEAKERS
    MIXER -.->|User Speaks Mid-Sentence| BARGE_IN
    BARGE_IN -.->|Flush Audio Buffer| MIXER
****
