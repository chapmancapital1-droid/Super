from mcp.server.mcpserver import MCPServer
import json

mcp = MCPServer("Sample JARVIS Toolset")

@mcp.tool()
async def calculate_risk(project_name: str, budget: float) -> str:
    """Calculate the risk level of a project based on its budget."""
    risk = "high" if budget > 1000000 else "low"
    return json.dumps({"project": project_name, "risk": risk, "analysis": "Budget-based risk assessment."})

if __name__ == "__main__":
    mcp.run()
