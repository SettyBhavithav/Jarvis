import re

prompts = [
    "fetch file from downloads and send to 93985582839",
    "get a file from C:\Jarvis to send to Sunny",
    "grab the file from desktop and forward to 93985582839",
    "file from documents send to 123",
    "fetch a file from downloads and send it to 93985582839"
]

for p in prompts:
    match = re.search(r"file.*?from\s+(.*?)\s+(?:and\s+)?(?:send|forward).*?to\s+(.*)", p)
    if match:
        print(f"Match: {p} -> {match.group(1)} | {match.group(2)}")
    else:
        print(f"FAIL: {p}")
