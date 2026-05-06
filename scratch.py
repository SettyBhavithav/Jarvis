import re

prompts = [
    "look at my screen and tell me what the error is",
    "what is on my screen right now",
    "jarvis please look at the screen and read the email to me",
    "read my screen",
    "analyze the screen",
    "what bug is in this code on my screen",
    "summarize this pdf i'm reading on screen"
]

for p in prompts:
    if "screen" in p and any(w in p for w in ["look", "what", "read", "analyze", "see", "describe", "summarize"]):
        q = p
        if " and " in p:
            q = p.split(" and ", 1)[-1]
        elif "on my screen" in p:
             q = p.replace("on my screen", "").strip()
        print(f"Match: {p} -> {q}")
