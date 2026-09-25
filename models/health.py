"""
JARVIS V2 - Model Health & Circuit Breaker System
Tracks provider latency, consecutive failures, and automatically opens circuit on outages.
"""
import time
from typing import Dict, Any

class ProviderHealthTracker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.stats: Dict[str, Dict[str, Any]] = {}

    def _ensure_provider(self, provider_name: str):
        if provider_name not in self.stats:
            self.stats[provider_name] = {
                "consecutive_failures": 0,
                "total_requests": 0,
                "total_errors": 0,
                "last_failure_time": 0.0,
                "circuit_open": False,
                "last_latency": 0.0
            }

    def record_success(self, provider_name: str, latency: float):
        self._ensure_provider(provider_name)
        p = self.stats[provider_name]
        p["consecutive_failures"] = 0
        p["circuit_open"] = False
        p["total_requests"] += 1
        p["last_latency"] = latency

    def record_failure(self, provider_name: str):
        self._ensure_provider(provider_name)
        p = self.stats[provider_name]
        p["consecutive_failures"] += 1
        p["total_errors"] += 1
        p["last_failure_time"] = time.time()
        if p["consecutive_failures"] >= self.failure_threshold:
            p["circuit_open"] = True
            print(f"🚨 [Circuit Breaker: Provider '{provider_name}' opened after {p['consecutive_failures']} consecutive failures!]")

    def is_available(self, provider_name: str) -> bool:
        self._ensure_provider(provider_name)
        p = self.stats[provider_name]
        if not p["circuit_open"]:
            return True
        # Check if cooldown has elapsed
        if time.time() - p["last_failure_time"] > self.cooldown_seconds:
            print(f"🔄 [Circuit Breaker: Provider '{provider_name}' cooldown expired. Attempting half-open probe.]")
            p["circuit_open"] = False
            p["consecutive_failures"] = 0
            return True
        return False

# Global Health Tracker Singleton
provider_health = ProviderHealthTracker()
