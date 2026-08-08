import httpx
import sys
import os

# Add parent dir to path so we can import app.config
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings

def verify_connection(name, url, path="/"):
    print(f"Verifying {name} at {url}...")
    try:
        # Check if the URL is valid
        if not url.startswith("http"):
            print(f"  [!] Invalid URL: {url}")
            return False
            
        full_url = f"{url.rstrip('/')}{path}"
        resp = httpx.get(full_url, timeout=5.0)
        if resp.status_code == 200:
            print(f"  [+] {name} is REACHABLE!")
            return True
        else:
            print(f"  [-] {name} returned status {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [-] {name} connection FAILED: {e}")
        return False

def main():
    print("=== JARVIS LLM Connection Verifier ===\n")
    
    # 1. Default OpenAI-compatible (LM Studio)
    verify_connection("LM Studio (Default)", settings.openai_base_url, "/models")
    
    # 2. Ollama
    verify_connection("Ollama", settings.ollama_base_url, "/api/tags")
    
    # 3. Policy Overrides
    for policy in ["fast", "reasoning", "code"]:
        url = getattr(settings, f"model_{policy}_url")
        if url:
            verify_connection(f"Override: {policy}", url, "/models")
            
    print("\nVerification complete.")

if __name__ == "__main__":
    main()
