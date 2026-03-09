from typing import Dict, Any, Callable
from pydantic import BaseModel, Field
import logging

from metagpt.utils.tool_loader import discover_python_files, discover_llm_tool_dirs, discover_callable_tools_in_file, load_llm_tool, _adapt_old_tool_to_new_metadata
from metagpt.config2 import config
from metagpt.const import METAGPT_ROOT
from pathlib import Path

from metagpt.tools.tool_registry import TOOL_REGISTRY as OLD_TOOL_REGISTRY

logger = logging.getLogger(__name__)

class ToolMetadata(BaseModel):
    name: str
    description: str
    usage_example: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    cost_model: str = ""
    access_requirements: str = ""
    tool_function: Callable = Field(exclude=True) # The actual callable tool function

class ToolRegistry:
    _instance = None
    _registry: Dict[str, ToolMetadata] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance

    def register_tool(self, tool_metadata: ToolMetadata):
        if tool_metadata.name in self._registry:
            logger.warning(f"Tool '{tool_metadata.name}' already registered. Skipping registration to prevent overwrite.")
            return # Prevent overwrite
        self._registry[tool_metadata.name] = tool_metadata

    def get_tool(self, name: str) -> ToolMetadata | None:
        return self._registry.get(name)

    def list_tools(self) -> Dict[str, ToolMetadata]:
        return self._registry

    def clear_registry(self):
        self._registry = {}

# Initial population mechanism (can be extended later for dynamic loading)
def populate_default_tools(registry: ToolRegistry):
    # Example tool (placeholder)
    def example_search_tool(query: str) -> str:
        return f"Searching for: {query}... results from a dummy search engine."

    registry.register_tool(ToolMetadata(
        name="example_search",
        description="A placeholder search tool.",
        usage_example="example_search('MetaGPT')",
        input_schema={"query": {"type": "string"}},
        output_schema={"result": {"type": "string"}},
        tool_function=example_search_tool
    ))

def load_and_register_all_tools(registry: ToolRegistry):
    """
    Discovers all tools from configured directories and registers them with the ToolRegistry.
    """
    tool_dirs = config.tool_dirs # Use the new config option

    # Discover and register Python callable tools
    python_files = discover_python_files(tool_dirs)
    for file_path in python_files:
        tools_in_file = discover_callable_tools_in_file(file_path)
        for tool_metadata in tools_in_file:
            registry.register_tool(tool_metadata)

    # Discover and register LLM-prompt-based tools
    llm_tool_dirs = discover_llm_tool_dirs(tool_dirs)
    for tool_dir in llm_tool_dirs:
        tool_metadata = load_llm_tool(tool_dir)
        if tool_metadata:
            registry.register_tool(tool_metadata)

    # Discover and register old-style tools via adapter
    for old_tool_name, old_tool in OLD_TOOL_REGISTRY.items():
        adapted_tools = _adapt_old_tool_to_new_metadata(old_tool)
        for tool_metadata in adapted_tools:
            registry.register_tool(tool_metadata)

# Instantiate and optionally populate with default tools
tool_registry = ToolRegistry()
populate_default_tools(tool_registry) # Keep example tools if desired, or remove
load_and_register_all_tools(tool_registry) # Call the new function to load all tools
