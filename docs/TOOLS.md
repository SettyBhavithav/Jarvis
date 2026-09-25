# JARVIS V2 — Comprehensive Tool Suite Specification

## 1. Tool Execution Engine
All tools in JARVIS V2 inherit from `BaseTool` (`tools/base_tool.py`) and are registered in `ToolRegistry` (`tools/registry.py`).
- **Pydantic Validation:** Strict typed schemas for all input arguments.
- **Timeout Isolation:** Tool execution runs in a thread pool with configurable timeout (default 30 seconds), preventing hangs.
- **Policy Enforcement:** Pre-execution check against `policy_engine` (Levels 0–4).
- **Deterministic Auditing:** All executions log arguments, return status, and duration to the audit trail.

---

## 2. Tool Inventory

### System & OS (`tools/system/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `system_get_stats` | Level 0 | Retrieves CPU load, RAM usage, disk space, and battery status. |
| `system_lock` | Level 4 | Locks the Windows workstation (`rundll32 user32.dll,LockWorkStation`). |
| `system_shutdown` | Level 4 | Shuts down the machine with 60-second abort window. Requires confirmation. |
| `system_list_windows` | Level 1 | Enumerates active top-level application windows. |
| `system_focus_window` | Level 1 | Brings specified application window to the foreground. |

### Media & Audio (`tools/media/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `media_toggle_play_pause`| Level 1 | Sends hardware play/pause media key event to Windows. |
| `media_volume_control` | Level 1 | Adjusts Windows master volume (mute, unmute, set level). |
| `media_spotify_control` | Level 1 | Controls Spotify desktop client track skipping and playback. |

### Communication & Productivity (`tools/communication/`, `tools/productivity/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `communication_gmail_list`| Level 2 | Lists recent emails or searches unread threads. |
| `communication_gmail_send`| Level 3 | Drafts or dispatches Gmail messages. Requires confirmation. |
| `communication_whatsapp_send`| Level 3 | Automates WhatsApp message dispatch via desktop protocol. |
| `productivity_calendar_list`| Level 1 | Queries upcoming Google Calendar appointments. |
| `productivity_calendar_create`| Level 2 | Schedules appointments on Google Calendar. |
| `task_add` | Level 2 | Adds an action item to persistent storage. |
| `task_list` | Level 1 | Enumerates active to-do items. |
| `task_complete` | Level 2 | Marks a task as finished. |

### Web & Research (`tools/browser/`, `tools/youtube/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `browser_search` | Level 1 | Executes DuckDuckGo web search returning top results. |
| `browser_navigate` | Level 1 | Opens URL in Playwright Chromium and captures text/DOM. |
| `browser_scrape_and_analyze`| Level 2 | Scrapes target URL and synthesizes findings against user goal. |
| `youtube_play` | Level 1 | Searches and launches target YouTube video in browser. |
| `youtube_summarize_transcript`| Level 1 | Fetches official video subtitles and generates bullet summary. |

### Vision & Multimodal (`tools/vision/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `vision_analyze_screen` | Level 1 | Captures current desktop screen and analyzes via vision LLM. |
| `multimodal_phi4_inspect`| Level 1 | Performs simultaneous audio and visual scene perception. |

### File Exploration (`tools/files/`)
| Tool Name | Risk Level | Description |
|---|---|---|
| `files_list_directory` | Level 1 | Enumerates files in Desktop, Documents, or Downloads with path-traversal guards. |
