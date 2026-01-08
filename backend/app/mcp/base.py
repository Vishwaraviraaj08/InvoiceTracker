"""
Base MCP Server
Abstract base class for Model Context Protocol servers
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class MCPToolDefinition(BaseModel):
    """Definition of an MCP tool"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str] = []


class MCPToolResult(BaseModel):
    """Result from an MCP tool execution"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseMCPServer(ABC):
    """
    Abstract base class for MCP servers.
    Each MCP server exposes structured tools callable by LangChain agents.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._tools: Dict[str, MCPToolDefinition] = {}
        self._register_tools()
    
    @abstractmethod
    def _register_tools(self) -> None:
        """Register tools provided by this server"""
        pass
    
    def get_tools(self) -> List[MCPToolDefinition]:
        """Get all available tools"""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        """Get a specific tool by name"""
        return self._tools.get(name)
    
    def register_tool(self, tool: MCPToolDefinition) -> None:
        """Register a new tool"""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} on server: {self.name}")
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool with given arguments"""
        pass
    
    def validate_args(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Validate arguments for a tool. Returns error message if invalid."""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Unknown tool: {tool_name}"
        
        for param in tool.required_params:
            if param not in args:
                return f"Missing required parameter: {param}"
        
        return None
    
    def to_langchain_tools(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to LangChain tool format"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]
