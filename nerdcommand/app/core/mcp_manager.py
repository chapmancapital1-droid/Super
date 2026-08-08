import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPManager:
    """Manages lifecycle of MCP servers and provides a unified tool interface."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.servers: Dict[str, Dict[str, Any]] = {}
        self._tools: Dict[str, Dict[str, Any]] = {} # tool_name -> {server_name, description, schema}
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack = None

    async def start(self):
        if not self.config_path.exists():
            logger.warning(f"MCP config not found at {self.config_path}")
            return

        with open(self.config_path, "r") as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})
        for name, cfg in mcp_servers.items():
            try:
                await self._connect_to_server(name, cfg)
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {name}: {e}")

    async def _connect_to_server(self, name: str, cfg: Dict[str, Any]):
        params = StdioServerParameters(
            command=cfg["command"],
            args=cfg.get("args", []),
            env={**os.environ, **cfg.get("env", {})}
        )
        
        # We start the client in a way that we can keep it alive
        # Note: This is a simplified version. Real lifecycle management 
        # would need to handle reconnects and process monitoring.
        
        # Using a background task to keep the session alive
        asyncio.create_task(self._session_loop(name, params))

    async def _session_loop(self, name: str, params: StdioServerParameters):
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._sessions[name] = session
                    
                    # Discover tools
                    response = await session.list_tools()
                    for tool in response.tools:
                        full_name = f"{name}__{tool.name}"
                        self._tools[full_name] = {
                            "server": name,
                            "original_name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.input_schema
                        }
                        logger.info(f"Discovered MCP tool: {full_name}")
                    
                    # Keep alive until shutdown
                    while name in self._sessions:
                        await asyncio.sleep(1)
        except Exception as e:
            import traceback
            logger.error(f"MCP session {name} error: {e}")
            logger.error(traceback.format_exc())
            if name in self._sessions:
                del self._sessions[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": k, "description": v["description"], "schema": v["input_schema"]}
            for k, v in self._tools.items()
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown MCP tool: {tool_name}")
        
        tool_info = self._tools[tool_name]
        server_name = tool_info["server"]
        session = self._sessions.get(server_name)
        
        if not session:
            raise RuntimeError(f"MCP server {server_name} not connected")
            
        result = await session.call_tool(tool_info["original_name"], arguments)
        
        # Format result for JARVIS
        content_text = ""
        for content in result.content:
            if hasattr(content, "text"):
                content_text += content.text
            elif isinstance(content, dict) and "text" in content:
                content_text += content["text"]
                
        return {
            "tool": tool_name,
            "ok": not result.isError,
            "result": content_text
        }

mcp_manager = MCPManager(Path("/home/user/Super/nerdcommand/mcp_config.json"))
