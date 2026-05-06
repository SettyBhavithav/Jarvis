import re
import time
from playwright.sync_api import sync_playwright
import google.genai as genai
from google.genai import types
import os

def extract_url(text):
    """Finds the first URL in a string."""
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(1) if match else None

def scrape_and_analyze(prompt, nim_client=None, groq_client=None):
    """
    Uses Playwright to navigate to a site headless, extract the visible text,
    and then asks the LLM to answer the user's prompt based on that text.
    """
    url = extract_url(prompt)
    if not url:
        return "Sir, please provide a valid URL for me to analyze."

    print(f"\n🕷️ [Playwright: Booting Headless Browser to scrape {url}...]")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate and wait for the DOM to load
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Let it run any dynamic JS for a couple seconds
            time.sleep(2)
            
            # Extract all visible text from the body
            raw_text = page.evaluate("document.body.innerText")
            browser.close()
            
            if not raw_text or len(raw_text.strip()) < 50:
                return "I successfully visited the page, sir, but I couldn't extract any meaningful text. It might be heavily protected or purely image-based."
                
            # Clean up the text and limit to ~25,000 chars to avoid token overflow
            clean_text = " ".join(raw_text.split())
            if len(clean_text) > 25000:
                clean_text = clean_text[:25000] + "... [TRUNCATED]"
                
            print(f"✅ [Playwright: Successfully extracted {len(clean_text)} characters.]")
            print("🧠 [Brain: Analyzing the scraped data...]")
            
            # Ask the AI to answer the user's prompt based on the scraped text
            ai_prompt = (
                f"You are Jarvis. The user asked: '{prompt}'.\n\n"
                f"I have successfully scraped the website for you. Based ONLY on the following text from the website, answer the user's request.\n"
                f"Website Text:\n{clean_text}"
            )
            
            # Use groq if available for speed, fallback to NIM
            if groq_client:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "user", "content": ai_prompt}],
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            elif nim_client:
                response = nim_client.chat.completions.create(
                    model="meta/llama-3.1-70b-instruct",
                    messages=[{"role": "user", "content": ai_prompt}],
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            else:
                return f"I successfully scraped the site, sir. Here is a preview of the text: {clean_text[:500]}..."
                
    except Exception as e:
        return f"I encountered an error while trying to scrape the website, sir: {e}"
