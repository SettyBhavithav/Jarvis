"""
JARVIS V2 - Autonomous Agentic Orchestrator & ReAct Controller
Plans multi-step tasks, processes memory commands, manages structured LLM tool calling,
and drives full ReAct observation loops with EventBus integration.
"""
import os
import sys
import re
import json
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from datetime import datetime
from typing import List, Dict, Any, Generator, Optional
from core.config import config
from core.schemas import ChatMessage, MessageRole, Plan, PlanStep, RiskLevel
from core.events import (
    event_bus,
    UserInputReceivedEvent,
    IntentDetectedEvent,
    ToolStartedEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
    VerificationCompletedEvent,
    ResponseGeneratedEvent,
    MemoryCreatedEvent
)
from memory.manager import memory_manager
from models.gateway import model_gateway
from tools.registry import tool_registry
from security.confirmations import confirmation_manager
from core.planner import agent_planner

class AgentOrchestrator:
    def __init__(self):
        self.memory = memory_manager
        self.gateway = model_gateway
        self.registry = tool_registry
        self.planner = agent_planner

    def load_soul_context(self) -> str:
        """Loads core personality profile and dynamic runtime context."""
        soul_content = "You are JARVIS, an autonomous AI system created for Setty Bhavithav."
        soul_path = "SOUL.md"
        if os.path.exists(soul_path):
            with open(soul_path, "r", encoding="utf-8") as f:
                soul_content = f.read()

        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")

        location_str = "Hyderabad, India"
        try:
            res = requests.get('https://ipapi.co/json/', timeout=1.5).json()
            city = res.get("city", "Hyderabad")
            region = res.get("region", "Telangana")
            country = res.get("country_name", "India")
            location_str = f"{city}, {region}, {country}"
        except Exception:
            pass

        dynamic_block = (
            f"\n\n--- CURRENT SYSTEM CONTEXT ---\n"
            f"Current Time: {time_str}\n"
            f"Current Date: {date_str}\n"
            f"User Location: {location_str}\n"
        )
        return soul_content + dynamic_block

    def process_memory_commands(self, prompt: str, user_id: str = "user_default", auth_token: Optional[str] = None) -> Optional[str]:
        """Direct CRUD routing for explicit user memory commands."""
        txt = prompt.lower().strip()

        # "What do you remember about me?" / "List memories"
        if any(w in txt for w in ["what do you remember", "list my memories", "show my memories", "what do you know about me"]):
            all_mems = self.memory.storage.get_all_memories(limit=15, user_id=user_id, auth_token=auth_token)
            if not all_mems:
                return "Sir, I do not have any stored facts in my memory database yet."
            reply = "Sir, here is what I currently remember about you:\n"
            for i, m in enumerate(all_mems):
                reply += f"{i+1}. {m['text']} (Category: {m['category']})\n"
            return reply

        # "Forget that..." / "Delete memory"
        forget_match = re.search(r"(?:forget|delete memory|erase memory)(?: that)? (.*)", prompt, re.IGNORECASE)
        if forget_match:
            snippet = forget_match.group(1).strip()
            if self.memory.storage.delete_memory(snippet, user_id=user_id, auth_token=auth_token):
                return f"I have deleted the memory containing '{snippet}', sir."
            return f"I could not locate any memory matching '{snippet}', sir."

        # "Clear all memories"
        if any(w in txt for w in ["clear my memories", "delete all memories", "erase memories"]):
            if self.memory.storage.clear_all_memories(user_id=user_id, auth_token=auth_token):
                return "I have cleared all records from long-term memory, sir."
            return "Failed to clear memory database, sir."

        return None

    def process_fast_path(
        self,
        user_text: str,
        user_id: str = "user_default",
        channel: str = "voice",
        session_id: str = "default_session",
        auth_token: Optional[str] = None
    ) -> Optional[str]:
        """Sub-second heuristic fast-path for direct hardware and media operations with strict identity-bound confirmations."""
        txt = user_text.lower().strip()

        # Confirmation handling: strictly bound to caller's token, user_id, session_id, and channel
        confirm_triggers = ["yes", "confirm", "proceed", "do it", "go ahead"]
        if any(txt == w or txt.startswith(f"{w} ") for w in confirm_triggers):
            words = txt.split()
            token = None
            # Check if user provided explicit token e.g. "confirm 3a8b1c2d"
            if len(words) > 1 and len(words[1]) == 8:
                token = words[1]
            else:
                # Look up pending token strictly scoped to this user, session, and channel
                token = confirmation_manager.get_pending_token_for_session(
                    user_id=user_id,
                    session_id=session_id,
                    channel=channel
                )

            if not token:
                return "Sir, there are no pending confirmation requests awaiting approval for your session."

            success, res = confirmation_manager.confirm(
                token=token,
                user_id=user_id,
                session_id=session_id,
                channel=channel
            )
            return f"Understood, sir. {res}"

        if txt in ["no", "cancel", "stop that", "abort"]:
            return confirmation_manager.cancel(
                user_id=user_id,
                session_id=session_id,
                channel=channel
            )

        # Memory commands
        mem_reply = self.process_memory_commands(user_text, user_id=user_id, auth_token=auth_token)
        if mem_reply:
            return mem_reply

        # System Diagnostics
        if any(w in txt for w in ["system status", "battery level", "cpu usage", "pc health", "pc status", "performance"]):
            return self.registry.execute_tool("system_get_stats", {}, user_id, channel, session_id, auth_token)

        # Media Controls
        if any(w in txt for w in ["pause the music", "stop the music", "play the music", "resume music", "pause music", "toggle music"]):
            return self.registry.execute_tool("media_toggle_play_pause", {}, user_id, channel, session_id, auth_token)
        if any(w in txt for w in ["next track", "skip song", "next song"]):
            return self.registry.execute_tool("media_next_track", {}, user_id, channel, session_id, auth_token)
        if any(w in txt for w in ["previous track", "last song", "previous song"]):
            return self.registry.execute_tool("media_previous_track", {}, user_id, channel, session_id, auth_token)
        if any(w in txt for w in ["mute audio", "mute volume", "unmute"]):
            return self.registry.execute_tool("media_mute_volume", {}, user_id, channel, session_id, auth_token)

        # Tasks
        if any(w in txt for w in ["show tasks", "to-do list", "my tasks", "view tasks"]):
            return self.registry.execute_tool("task_list", {}, user_id, channel, session_id, auth_token)
        if any(w in txt for w in ["clear tasks", "empty to-do list", "delete all tasks"]):
            return self.registry.execute_tool("task_clear", {}, user_id, channel, session_id, auth_token)

        # Calendar
        if any(w in txt for w in ["calendar", "upcoming events", "my schedule", "what am i doing"]):
            return self.registry.execute_tool("calendar_list_events", {}, user_id, channel)

        # Desktop Window Minimization
        if any(w in txt for w in ["minimize windows", "show desktop", "minimize everything"]):
            return self.registry.execute_tool("system_minimize_all", {}, user_id, channel)

        return None

    def execute_turn(
        self,
        user_text: str,
        history: List[ChatMessage],
        user_id: str = "user_default",
        channel: str = "voice",
        session_id: str = "default_session",
        auth_token: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Full ReAct Execution Cycle:
        1. EventBus UserInputReceived
        2. Fast-Path Heuristic Check (strictly bound to caller session & channel)
        3. Multi-Step Planning Check
        4. Memory Extraction & RAG Retrieval
        5. Structured LLM Tool Calling with Observation Loop
        6. Response Streaming & Metrics
        """
        event_bus.publish_sync(UserInputReceivedEvent(
            source=channel,
            text=user_text,
            user_id=user_id
        ))

        # 1. Fast-Path Check
        fast_reply = self.process_fast_path(
            user_text,
            user_id=user_id,
            channel=channel,
            session_id=session_id,
            auth_token=auth_token
        )
        if fast_reply:
            event_bus.publish_sync(ResponseGeneratedEvent(response_length=len(fast_reply), channel=channel))
            yield fast_reply
            return

        # 2. Multi-Step Task Planner Check
        if self.planner.is_complex_task(user_text):
            print(f"🧠 [Planner: Complex Multi-Step Goal Detected: '{user_text}']")
            plan = self.planner.create_plan(user_text, user_id=user_id)
            plan_res = self.planner.execute_plan(
                plan,
                user_id=user_id,
                channel=channel,
                session_id=session_id,
                auth_token=auth_token
            )
            event_bus.publish_sync(ResponseGeneratedEvent(response_length=len(plan_res), channel=channel))
            yield plan_res
            return

        # 3. Extract facts to Long-Term Memory
        extracted = self.memory.process_turn_for_memory(user_text, user_id=user_id, auth_token=auth_token)
        if extracted:
            event_bus.publish_sync(MemoryCreatedEvent(memory_text=extracted))

        # 4. Retrieve relevant RAG memories & Document context
        memories = self.memory.retrieve_relevant_memories(
            user_text,
            top_k=3,
            threshold=0.3,
            user_id=user_id,
            auth_token=auth_token
        )
        memory_context = ""
        if memories:
            memory_context = "\n--- RELEVANT RETRIEVED MEMORIES ---\n"
            for m in memories:
                memory_context += f"- {m['text']}\n"

        # Context Router: Document RAG retrieval when relevant
        if any(w in user_text.lower() for w in ["document", "file", "paper", "pdf", "report", "notes", "manual"]):
            docs = self.memory.doc_rag.search_documents(user_text, limit=2, user_id=user_id)
            if docs:
                memory_context += "\n--- RETRIEVED DOCUMENT EXCERPTS ---\n"
                for d in docs:
                    memory_context += f"- [{d['citation']}]: {d['content']}\n"

        # 5. Build Context with OpenAI-compatible tool specifications
        system_prompt = self.load_soul_context() + memory_context

        tool_schemas = self.registry.get_schemas()
        context_messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]
        context_messages.extend(history[-6:])
        context_messages.append(ChatMessage(role=MessageRole.USER, content=user_text))

        # 6. Safety Filter
        if not self.gateway.check_safety(user_text):
            refusal = "I'm sorry, sir, but my safety protocols prevent me from fulfilling that request."
            event_bus.publish_sync(ResponseGeneratedEvent(response_length=len(refusal), channel=channel))
            yield refusal
            return

        # 7. Native Structured LLM Tool Calling & ReAct Observation Loop
        react_executed_any = False
        for iteration in range(3):
            model_res = self.gateway.generate_with_tools(context_messages, tools=tool_schemas)
            
            if not model_res.tool_calls:
                # Conversational response or ReAct final response
                if model_res.content and not react_executed_any:
                    event_bus.publish_sync(ResponseGeneratedEvent(response_length=len(model_res.content), channel=channel))
                    yield model_res.content
                    return
                elif model_res.content and react_executed_any:
                    event_bus.publish_sync(ResponseGeneratedEvent(response_length=len(model_res.content), channel=channel))
                    yield model_res.content
                    return
                break

            react_executed_any = True

            # Preserve assistant message with native tool_calls structure
            context_messages.append(ChatMessage(
                role=MessageRole.ASSISTANT,
                content=model_res.content or "",
                tool_calls=model_res.tool_calls
            ))

            # Execute each tool call and append corresponding tool role message
            for tc in model_res.tool_calls:
                tool_name = tc.name
                args = tc.arguments
                print(f"🛠️ [Native Provider Tool Call: {tool_name} with arguments: {args}]")
                event_bus.publish_sync(ToolStartedEvent(tool_name=tool_name, arguments=args))

                try:
                    tool_result = self.registry.execute_tool(
                        tool_name,
                        args,
                        user_id=user_id,
                        channel=channel,
                        session_id=session_id,
                        auth_token=auth_token
                    )
                    event_bus.publish_sync(ToolCompletedEvent(tool_name=tool_name, result=tool_result, success=True))
                    context_messages.append(ChatMessage(
                        role=MessageRole.TOOL,
                        content=str(tool_result),
                        name=tool_name,
                        tool_call_id=tc.id
                    ))
                except Exception as e:
                    event_bus.publish_sync(ToolFailedEvent(tool_name=tool_name, error=str(e), recovery_attempted=True))
                    context_messages.append(ChatMessage(
                        role=MessageRole.TOOL,
                        content=f"Tool error: {e}. Adjust arguments or use alternative tool.",
                        name=tool_name,
                        tool_call_id=tc.id
                    ))

        # Stream final synthesized response to user
        full_response = []
        for token in self.gateway.stream_generate(context_messages):
            full_response.append(token)
            yield token

        event_bus.publish_sync(ResponseGeneratedEvent(response_length=len("".join(full_response)), channel=channel))

# Global Orchestrator Singleton
orchestrator = AgentOrchestrator()
