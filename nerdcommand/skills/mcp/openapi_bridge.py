import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.mcpserver import MCPServer
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openapi-bridge")

def create_openapi_server(name: str, openapi_url: str):
    mcp = MCPServer(f"OpenAPI Bridge: {name}")
    
    # We'll discover tools asynchronously at startup
    # Since MCPServer.run() is blocking and doesn't easily expose the raw server 
    # to add tools dynamically after fetching a remote spec, 
    # we'll use a helper to pre-fetch if possible.
    
    spec = {}
    try:
        logger.info(f"Attempting to fetch OpenAPI spec from {openapi_url}...")
        with httpx.Client() as client:
            resp = client.get(openapi_url, timeout=5.0)
            resp.raise_for_status()
            spec = resp.json()
            logger.info("Successfully fetched OpenAPI spec.")
    except Exception as e:
        logger.error(f"Could not fetch OpenAPI spec from {openapi_url}: {e}")
        # We can't define tools without the spec. 
        # In a real implementation, we might retry or wait.
        # For this bridge, we'll assume the spec might be provided locally if remote fails.
        return mcp

    # Register generic tool even if spec fetch fails
    @mcp.tool()
    async def call_api(
        path: str = Field(description="The API endpoint path (e.g. /users)"),
        method: str = Field(default="GET", description="HTTP method: GET, POST, etc."),
        payload: Optional[Dict[str, Any]] = Field(default=None, description="JSON body or query parameters")
    ) -> str:
        """Execute a generic call to the bridged OpenAPI service."""
        # Use the base URL derived or default
        effective_base = spec.get("servers", [{}])[0].get("url", openapi_url.split("/openapi.json")[0])
        
        async with httpx.AsyncClient() as client:
            url = f"{effective_base.rstrip('/')}/{path.lstrip('/')}"
            try:
                if method.upper() == "GET":
                    r = await client.request(method, url, params=payload, timeout=30.0)
                else:
                    r = await client.request(method, url, json=payload, timeout=30.0)
                r.raise_for_status()
                return r.text
            except Exception as e:
                return f"Error calling {method} {path}: {str(e)}"

    # Process paths if spec available
    paths = spec.get("paths", {})
    # ... (we could add dynamic tools here if we used low-level SDK)
    
    return mcp

if __name__ == "__main__":
    import sys
    # Defaulting to the user's provided 8787 service
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787/openapi.json"
    server = create_openapi_server("External Service", url)
    server.run()
