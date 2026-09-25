"""
JARVIS V2 - Operational Metrics Tracker
Tracks tool success rates, model response latency, and interruption frequency.
"""
from typing import Dict, Any

class MetricsTracker:
    def __init__(self):
        self.tool_invocations: int = 0
        self.tool_successes: int = 0
        self.tool_failures: int = 0
        self.barge_in_count: int = 0

    def record_tool_run(self, success: bool):
        self.tool_invocations += 1
        if success:
            self.tool_successes += 1
        else:
            self.tool_failures += 1

    def record_barge_in(self):
        self.barge_in_count += 1

    def get_summary(self) -> Dict[str, Any]:
        rate = (self.tool_successes / self.tool_invocations * 100) if self.tool_invocations > 0 else 100.0
        return {
            "total_tool_runs": self.tool_invocations,
            "tool_success_rate": f"{rate:.1f}%",
            "barge_in_interruptions": self.barge_in_count
        }

metrics_tracker = MetricsTracker()
