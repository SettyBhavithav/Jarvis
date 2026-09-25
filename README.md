%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'mainBkg': '#111827',
    'textColor': '#ffffff',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#ffffff',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#60a5fa',
    'secondaryColor': '#1e1b4b',
    'tertiaryColor': '#064e3b',
    'fontFamily': 'Inter, system-ui, sans-serif',
    'fontSize': '13px'
  }
}}%%

flowchart TD
    %% =========================================================================
    %% HIGH-CONTRAST DARK PALETTES
    %% =========================================================================
    classDef inputStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef audioStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#ffffff;
    classDef secStyle fill:#311b05,stroke:#f59e0b,stroke-width:2px,color:#ffffff;
    classDef agentStyle fill:#2e1065,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef modelStyle fill:#172554,stroke:#60a5fa,stroke-width:2px,color:#ffffff;
    classDef toolStyle fill:#042f2e,stroke:#2dd4bf,stroke-width:2px,color:#ffffff;
    classDef storeStyle fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef outStyle fill:#431407,stroke:#fb923c,stroke-width:2px,color:#ffffff;

    %% =========================================================================
    %% TIER 1: MULTI-MODAL INGESTION
    %% =========================================================================
    subgraph T1 ["  1. MULTI-MODAL SENSORY INGESTION  "]
        IN_MIC["🎙️ Microphone Stream<br/><b>16kHz PyAudio</b>"]:::inputStyle
        IN_DISCORD["📱 Discord OpenClaw<br/><b>Remote Mobile Bot</b>"]:::inputStyle
        IN_CLI["💻 Terminal CLI / API<br/><b>FastAPI Webhooks</b>"]:::inputStyle
        IN_SCREEN["👁️ Screen Capture<br/><b>PyAutoGUI Silent Frame</b>"]:::inputStyle
    end

    %% =========================================================================
    %% TIER 2: CONTINUOUS AUDIO & SPEECH-TO-TEXT
    %% =========================================================================
    subgraph T2 ["  2. CONTINUOUS AUDIO & ULTRA-FAST STT  "]
        OWW["👂 openwakeword ONNX<br/><b>'hey_jarvis' @ 0.15 threshold</b>"]:::audioStyle
        VAD["🎛️ Audio Normalization<br/><b>VAD 500ms Silence Filter</b>"]:::audioStyle
        STT_GROQ["⚡ Groq LPU Cloud STT<br/><b>whisper-large-v3-turbo (~80ms)</b>"]:::audioStyle
        STT_LOCAL["📴 Local faster-whisper<br/><b>small.en CPU/GPU Fallback</b>"]:::audioStyle
    end

    IN_MIC --> OWW
    OWW -->|Wake Word Detected| VAD
    VAD --> STT_GROQ
    VAD -.->|Offline Disconnect| STT_LOCAL

    %% =========================================================================
    %% TIER 3: SECURITY, POLICY & RISK ENGINE
    %% =========================================================================
    subgraph T3 ["  3. ZERO-TRUST SECURITY & RISK POLICIES  "]
        AUTH_GATE["🔑 GoTrue Identity Gate<br/><b>Cryptographic Bearer JWT</b>"]:::secStyle
        POLICY["⚖️ Risk Policy Engine<br/><b>Action Levels 0 to 4</b>"]:::secStyle
        INJECT["🔒 Context Isolator<br/><b>&lt;&lt;&lt;BEGIN_UNTRUSTED_DATA&gt;&gt;&gt;</b>"]:::secStyle
        CONFIRM["⚠️ Explicit Confirmation<br/><b>Voice / Discord Approval (L3/L4)</b>"]:::secStyle
    end

    IN_DISCORD --> AUTH_GATE
    IN_CLI --> AUTH_GATE
    STT_GROQ --> AUTH_GATE
    STT_LOCAL --> AUTH_GATE
    IN_SCREEN --> AUTH_GATE

    AUTH_GATE --> POLICY
    POLICY -->|Level 0-2: Read-Only Actions| INJECT
    POLICY -->|Level 3-4: Destructive Actions| CONFIRM
    CONFIRM -->|User Confirmed| INJECT

    %% =========================================================================
    %% TIER 4: AUTONOMOUS REACT AGENT & PLANNER
    %% =========================================================================
    subgraph T4 ["  4. AUTONOMOUS REACT PLANNING CORE  "]
        PLANNER["📋 Goal Planner & Decomposer<br/><b>Multi-Step Task State Tracker</b>"]:::agentStyle
        ROUTER["🧭 Capability Intent Router<br/><b>Classifies Modality & Complexity</b>"]:::agentStyle
        RECOVERY["🔄 Goal-Preserving Recovery<br/><b>Adaptive Replanning on Errors</b>"]:::agentStyle
    end

    INJECT --> PLANNER
    PLANNER --> ROUTER
    RECOVERY --> PLANNER

    %% =========================================================================
    %% TIER 5: NEURAL MODEL GATEWAY
    %% =========================================================================
    subgraph T5 ["  5. UNIFIED NEURAL MODEL GATEWAY  "]
        M_GROQ["⚡ Groq LPU (Primary Chat)<br/><b>qwen/qwen3.8-27b</b>"]:::modelStyle
        M_NIM["👁️ NVIDIA NIM (Vision & Backup)<br/><b>llama-3.2-11b-vision / nemotron</b>"]:::modelStyle
        M_DEEPSEEK["🔬 DeepSeek (Engineering)<br/><b>deepseek-chat & deepseek-reasoner</b>"]:::modelStyle
        M_GEMINI["🌐 Google Gemini (Fallback)<br/><b>gemini-2.0-flash</b>"]:::modelStyle
        M_OLLAMA["📴 Local Ollama (Offline)<br/><b>llama3.1:8b Local Daemon</b>"]:::modelStyle
    end

    ROUTER -->|Chat / Direct Intent| M_GROQ
    ROUTER -->|Screen Perception| M_NIM
    ROUTER -->|Coding & Deep Logic| M_DEEPSEEK
    M_GROQ -.->|Rate Limit / Timeout| M_NIM
    M_NIM -.->|Fallback| M_GEMINI
    M_DEEPSEEK -.->|Fallback| M_NIM
    M_GROQ & M_NIM & M_DEEPSEEK -.->|No Internet| M_OLLAMA

    %% =========================================================================
    %% TIER 6: TYPED TOOL REGISTRY ("THE CLAW")
    %% =========================================================================
    subgraph T6 ["  6. TYPED TOOL REGISTRY ('THE CLAW')  "]
        T_SYS["📊 System Diagnostics<br/><b>psutil CPU, RAM, Disk, Battery</b>"]:::toolStyle
        T_WEB["🕷️ Playwright Automation<br/><b>Headless Chromium DOM Bypass</b>"]:::toolStyle
        T_MAIL["📧 Google Workspace<br/><b>Gmail & Calendar OAuth2</b>"]:::toolStyle
        T_MEDIA["🎵 Windows Media Controller<br/><b>Spotify & Volume OS Hooks</b>"]:::toolStyle
        T_WA["💬 WhatsApp Automation<br/><b>Local Document Search & Send</b>"]:::toolStyle
        T_YT["📺 YouTube Intelligence<br/><b>Transcript Extraction & Summary</b>"]:::toolStyle
    end

    M_GROQ & M_NIM & M_DEEPSEEK & M_OLLAMA -->|Native JSON Tool Call| T_SYS & T_WEB & T_MAIL & T_MEDIA & T_WA & T_YT
    T_SYS & T_WEB & T_MAIL & T_MEDIA & T_WA & T_YT -.->|Tool Failure| RECOVERY

    %% =========================================================================
    %% TIER 7: AUTHORITATIVE CLOUD PERSISTENCE VS LOCAL CACHE
    %% =========================================================================
    subgraph T7 ["  7. AUTHORITATIVE CLOUD STORAGE & RAG MEMORY  "]
        SUPA_AUTH["🛡️ Supabase PostgreSQL<br/><b>Row-Level Security auth.uid()</b>"]:::storeStyle
        SUPA_VEC["🧬 pgvector Memory RAG<br/><b>384-dim all-MiniLM-L6-v2 Embeddings</b>"]:::storeStyle
        SUPA_SCHED["⏰ Atomic Task Scheduler<br/><b>Safe Claim status='claimed'</b>"]:::storeStyle
        SUPA_AUDIT["📜 Security Audit Trail<br/><b>Immutable Append-Only Action Logs</b>"]:::storeStyle
        SQLITE_CACHE["💾 Local SQLite Resilience<br/><b>jarvis_local_cache.db Queue</b>"]:::storeStyle
    end

    PLANNER <-->|Hybrid Vector Memory Recall| SUPA_VEC
    PLANNER <-->|Persistent Tasks & Reminders| SUPA_SCHED
    T_SYS & T_WEB & T_MAIL & T_MEDIA & T_WA & T_YT -->|Action Hash Log| SUPA_AUDIT
    SUPA_AUTH --> SUPA_VEC & SUPA_SCHED & SUPA_AUDIT
    SUPA_VEC & SUPA_SCHED -.->|Offline Sync Queue| SQLITE_CACHE

    %% =========================================================================
    %% TIER 8: STREAMING VOICE SYNTHESIS & BARGE-IN
    %% =========================================================================
    subgraph T8 ["  8. STREAMING VOICE OUTPUT & INTERRUPT LOOP  "]
        CHUNK["✂️ Sentence Token Chunker<br/><b>Punctuation Splitter (. ! ?)</b>"]:::outStyle
        TTS["🔊 Edge-TTS Streaming<br/><b>en-US-GuyNeural Generator</b>"]:::outStyle
        MIXER["🎧 Pygame Audio Queue<br/><b>Non-Blocking Audio Playback</b>"]:::outStyle
        BARGE_IN["🛑 Barge-In Interruption<br/><b>Instant Buffer Flush + 0.8s Decay</b>"]:::outStyle
        SPEAKERS["🔊 Physical Laptop Speakers<br/><b>Audio Output into Room</b>"]:::outStyle
    end

    PLANNER -->|Direct Answer Stream| CHUNK
    CHUNK --> TTS
    TTS --> MIXER
    MIXER --> SPEAKERS
    MIXER -.->|User Barge-In Speech| BARGE_IN
    BARGE_IN -.->|Purge Pending Audio| MIXER
