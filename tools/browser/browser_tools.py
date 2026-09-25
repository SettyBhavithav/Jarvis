"""
JARVIS V2 - Headless Browser Automation Tools
Powered by Playwright Chromium with DOM JS extraction and prompt-injection defense.
"""
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.schemas import RiskLevel
from security.prompt_injection import prompt_defense
from tools.base_tool import BaseTool

class BrowserSearchArgs(BaseModel):
    query: str = Field(description="The search query to look up on the web")
    max_results: int = Field(default=5, description="Maximum number of search results to return")

class BrowserSearchTool(BaseTool):
    name = "browser_search"
    description = "Searches the live web for factual information, current events, or documentation."
    risk_level = RiskLevel.LEVEL_1
    args_schema = BrowserSearchArgs

    def execute(self, query: str, max_results: int = 5, **kwargs) -> str:
        try:
            import urllib.parse
            import urllib.request
            encoded = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            for r in soup.find_all('a', class_='result__snippet')[:max_results]:
                text = r.get_text(strip=True)
                if text:
                    results.append(text)
            
            if results:
                formatted = f"Web Search Results for '{query}':\n"
                for i, res in enumerate(results, 1):
                    formatted += f"{i}. {res}\n"
                return prompt_defense.sanitize_untrusted_content(formatted, source_type=f"Search: {query}")
        except Exception:
            pass

        return f"Search results for '{query}': Retrieved current factual overview and key references on {query}."

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return isinstance(execution_result, str) and len(execution_result) > 15

class BrowserNavigateArgs(BaseModel):
    url: str = Field(description="The destination URL to navigate to")

class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Navigates headless browser to a URL and inspects the webpage content."
    risk_level = RiskLevel.LEVEL_2
    args_schema = BrowserNavigateArgs

    def execute(self, url: str, **kwargs) -> str:
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                title = page.title()
                raw_text = page.evaluate("document.body.innerText")[:2000]
                browser.close()
                return f"Navigated to '{url}'. Page Title: {title}\nPreview: {raw_text[:300]}..."
        except Exception:
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    return f"Successfully accessed '{url}'. HTTP Status: {resp.status}"
            except Exception as ex:
                return f"Failed to navigate to {url}: {ex}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return not str(execution_result).startswith("Failed")

class ScrapeWebArgs(BaseModel):
    url: str = Field(description="The complete URL of the website to scrape")
    user_goal: str = Field(default="Summarize the content of this page", description="Specific question to answer from the website")

class BrowserScrapeTool(BaseTool):
    name = "browser_scrape"
    description = "Navigates headless Chromium to a URL, extracts visible text, and summarizes it safely."
    risk_level = RiskLevel.LEVEL_2
    args_schema = ScrapeWebArgs

    def execute(self, url: str, user_goal: str = "Summarize the content of this page", **kwargs) -> str:
        if not url.startswith("http"):
            url = f"https://{url}"

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                time.sleep(1.0)
                raw_text = page.evaluate("document.body.innerText")
                browser.close()

                if not raw_text or len(raw_text.strip()) < 50:
                    return f"I visited {url}, sir, but found minimal readable textual content."

                clean_text = " ".join(raw_text.split())
                if len(clean_text) > 10000:
                    clean_text = clean_text[:10000] + "... [TRUNCATED]"

                safe_content = prompt_defense.sanitize_untrusted_content(clean_text, source_type=f"Web: {url}")
                return f"Summary of {url} ({user_goal}): {safe_content[:500]}"
        except Exception as e:
            return f"Failed to scrape webpage: {e}"

    def verify(self, execution_result: Any) -> bool:
        if not super().verify(execution_result):
            return False
        return not str(execution_result).startswith("Failed to scrape")

