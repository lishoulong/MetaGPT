import pytest
from unittest.mock import Mock, patch
from metagpt.utils.tool_registry import ToolRegistry, ToolMetadata, populate_default_tools, load_and_register_all_tools
from metagpt.configs.llm_config import LLMConfig
from pathlib import Path
import logging
from typing import Literal

# Import Tool for mock
from metagpt.tools.tool_data_type import Tool
# Import _load_module_from_path for patching
from metagpt.utils.tool_loader import _load_module_from_path

# Ensure the mock_config_fixture is available from test_tool_loader.py
# If test_tool_loader.py is not imported, you might need to redefine mock_config_fixture here
# For now, assuming it's available via pytest's auto-discovery if in the same test suite run
@pytest.fixture(autouse=True)
def mock_config_fixture():
    with patch('metagpt.config2.config') as mock_cfg:
        mock_cfg.llm = LLMConfig() # Provide a default LLMConfig
        mock_cfg.tool_dirs = [] # Default to empty for controlled tests
        yield mock_cfg

@pytest.fixture(autouse=True)
def clear_tool_registry():
    """Clears the tool registry before each test."""
    ToolRegistry._instance = None # Reset the singleton
    registry = ToolRegistry()
    registry.clear_registry()
    yield
    # No need to clear after test, as autouse fixture will reset it before next test

@pytest.fixture
def mock_tool_metadata():
    """A mock ToolMetadata object for testing."""
    mock_func = Mock(__name__="mock_tool_func")
    return ToolMetadata(
        name="mock_tool",
        description="A mock tool for testing.",
        input_schema={"param": {"type": "string"}},
        tool_function=mock_func
    )

@pytest.fixture
def mock_llm_tool_metadata():
    """A mock ToolMetadata object for an LLM tool."""
    mock_llm_func = Mock(__name__="mock_llm_tool_func")
    mock_llm_func.return_value = "LLM response" # Make it return something for testing
    mock_llm_func.__name__ = "mock_llm_tool_func"
    return ToolMetadata(
        name="mock_llm_tool",
        description="A mock LLM tool for testing.",
        input_schema={"query": {"type": "string"}},
        tool_function=mock_llm_func
    )

@pytest.fixture
def temp_tool_discovery_env(tmp_path, mock_config_fixture):
    """Sets up a temporary environment for tool discovery."""
    tool_dir = tmp_path / "my_tools"
    tool_dir.mkdir()

    # Python tool
    python_tool_file = tool_dir / "my_python_tool.py"
    python_tool_file.write_text("""
from metagpt.utils.tool_registry import ToolMetadata
from typing import Dict, Any

def python_tool_func(arg1: str) -> Dict[str, Any]:
    \"\"\"
    ```json
    {
        "name": "python_tool",
        "description": "A Python callable tool.",
        "input_schema": {"arg1": {"type": "string"}},
        "output_schema": {"result": {"type": "string"}}
    }
    ```
    This is a python tool.
    \"\"\"
    return {"result": f"Python tool executed with {arg1}"}
""")

    # LLM tool
    llm_tool_dir = tool_dir / "my_llm_tool"
    llm_tool_dir.mkdir()
    (llm_tool_dir / "config.json").write_text("""
{
    "name": "llm_based_tool",
    "description": "An LLM-prompt-based tool.",
    "input_schema": {"prompt_input": {"type": "string"}},
    "usage_example": "llm_based_tool(prompt_input='hello')"
}
""")
    (llm_tool_dir / "prompt.txt").write_text("Generate a response for: {prompt_input}")

    mock_config_fixture.tool_dirs = [tool_dir]
    yield

class TestToolRegistry:
    def test_register_tool(self, mock_tool_metadata):
        registry = ToolRegistry()
        registry.register_tool(mock_tool_metadata)
        assert registry.get_tool("mock_tool") == mock_tool_metadata

    def test_register_duplicate_tool_logs_warning_and_prevents_overwrite(self, mock_tool_metadata, caplog):
        registry = ToolRegistry()
        registry.register_tool(mock_tool_metadata)

        with caplog.at_level(logging.WARNING):
            # Create a modified metadata with the same name
            modified_mock_tool = ToolMetadata(
                name="mock_tool",
                description="A modified mock tool.",
                input_schema={"new_param": {"type": "number"}},
                tool_function=Mock(__name__="modified_func")
            )
            registry.register_tool(modified_mock_tool)

            assert "already registered. Skipping registration to prevent overwrite" in caplog.text
            # Assert that the original tool is still in the registry
            assert registry.get_tool("mock_tool") == mock_tool_metadata
            assert registry.get_tool("mock_tool").description == "A mock tool for testing."

    def test_get_tool(self, mock_tool_metadata):
        registry = ToolRegistry()
        registry.register_tool(mock_tool_metadata)
        retrieved_tool = registry.get_tool("mock_tool")
        assert retrieved_tool == mock_tool_metadata
        assert registry.get_tool("non_existent_tool") is None

    def test_list_tools(self, mock_tool_metadata, mock_llm_tool_metadata):
        registry = ToolRegistry()
        registry.register_tool(mock_tool_metadata)
        registry.register_tool(mock_llm_tool_metadata)
        listed_tools = registry.list_tools()
        assert len(listed_tools) == 2
        assert "mock_tool" in listed_tools
        assert "mock_llm_tool" in listed_tools
        assert listed_tools["mock_tool"] == mock_tool_metadata
        assert listed_tools["mock_llm_tool"] == mock_llm_tool_metadata

    def test_clear_registry(self, mock_tool_metadata):
        registry = ToolRegistry()
        registry.register_tool(mock_tool_metadata)
        assert len(registry.list_tools()) == 1
        registry.clear_registry()
        assert len(registry.list_tools()) == 0

    def test_populate_default_tools(self):
        registry = ToolRegistry()
        populate_default_tools(registry)
        assert registry.get_tool("example_search") is not None

    @pytest.mark.asyncio
    async def test_load_and_register_all_tools(self, temp_tool_discovery_env, mock_config_fixture):
        registry = ToolRegistry()
        mock_config_fixture.llm = LLMConfig() # Ensure LLMConfig is available for load_llm_tool

        mock_llm_instance = AsyncMock()
        mock_llm_instance.aask.return_value = "LLM response for prompt_input."
        with patch('metagpt.llm.LLM', return_value=mock_llm_instance) as mock_llm_constructor:
            load_and_register_all_tools(registry)

            # Check Python tool
            python_tool = registry.get_tool("python_tool")
            assert python_tool is not None
            assert python_tool.description == "A Python callable tool."
            assert python_tool.tool_function("test_arg") == {"result": "Python tool executed with test_arg"}

            # Check LLM tool
            llm_tool = registry.get_tool("llm_based_tool")
            assert llm_tool is not None
            assert llm_tool.description == "An LLM-prompt-based tool."

            # Test LLM tool's callable wrapper
            result = await llm_tool.tool_function(prompt_input="test_prompt")
            mock_llm_constructor.assert_called_once_with(llm_config=mock_config_fixture.llm)
            mock_llm_instance.aask.assert_called_once_with("Generate a response for: test_prompt")
            assert result == "LLM response for prompt_input."

    @pytest.mark.asyncio
    async def test_load_and_register_old_browser_tool(self, mock_config_fixture, clear_tool_registry):
        # 1. Mock the Browser class and its methods
        mock_page = AsyncMock()
        mock_page.url = "http://mock.url"

        mock_browser_instance = AsyncMock()
        mock_browser_instance.new_context.return_value = AsyncMock()
        mock_browser_instance.new_context.return_value.new_page.return_value = mock_page

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch.return_value = mock_browser_instance
        mock_playwright.stop.return_value = None

        class MockBrowser:
            # Need to mock a minimal init for Pydantic BaseModel, but the actual instance
            # will be controlled by our patch
            def __init__(self, **data):
                pass # Pydantic will handle fields, we just need a constructor

            # Simulate the async methods of Browser
            async def start(self):
                self.playwright = mock_playwright
                self.browser_instance = mock_browser_instance
                self.page = mock_page
                return "started"

            async def stop(self):
                self.playwright = None
                return "stopped"

            async def click(self, element_id: int):
                # We can verify this mock is called
                self.click_mock(element_id)
                return "click_success"

            async def type(self, element_id: int, content: str, press_enter_after: bool = False):
                self.type_mock(element_id, content, press_enter_after)
                return "type_success"

            async def goto(self, url: str, timeout: float = 90000):
                self.goto_mock(url, timeout)
                return f"SUCCESS, URL: {url} have been loaded."

            async def scroll(self, direction: Literal["down", "up"]):
                self.scroll_mock(direction)
                return "scroll_success"

            # Attach mock objects to the class for verification
            click_mock = AsyncMock(return_value=None)
            type_mock = AsyncMock(return_value=None)
            goto_mock = AsyncMock(return_value=None)
            scroll_mock = AsyncMock(return_value=None)

            # Minimal _wait_page to avoid complex Playwright mocks
            async def _wait_page(self):
                return f"SUCCESS, URL: {mock_page.url} have been loaded."


        # 2. Mock the old Tool object for Browser
        # This structure comes from metagpt/tools/libs/browser.py's @register_tool decorator
        mock_old_browser_tool = MagicMock(spec=Tool)
        mock_old_browser_tool.name = "Browser"
        mock_old_browser_tool.path = "/metagpt/tools/libs/browser.py" # Dummy path
        mock_old_browser_tool.schemas = {
            "class_name": "Browser", # This should match the class name in the mocked module
            "include_functions": [ # These are the methods explicitly exposed
                "click", "type", "goto", "scroll"
            ],
            "methods": { # The old tool registry stores detailed schema here
                "click": {"description": "Clicks an element.", "parameters": {"element_id": {"type": "integer"}}, "returns": {"type": "string"}},
                "type": {"description": "Types text into an element.", "parameters": {"element_id": {"type": "integer"}, "content": {"type": "string"}}, "returns": {"type": "string"}},
                "goto": {"description": "Navigates to a URL.", "parameters": {"url": {"type": "string"}}, "returns": {"type": "string"}},
                "scroll": {"description": "Scrolls the page.", "parameters": {"direction": {"type": "string", "enum": ["down", "up"]}}, "returns": {"type": "string"}}
            }
        }


        # 3. Patch OLD_TOOL_REGISTRY and _load_module_from_path
        with patch('metagpt.tools.tool_registry.TOOL_REGISTRY', {"Browser": mock_old_browser_tool}), \
             patch('metagpt.utils.tool_loader._load_module_from_path') as mock_load_module:

            # Configure mock_load_module to return a mock module containing our MockBrowser class
            mock_module_with_browser = MagicMock()
            mock_module_with_browser.Browser = MockBrowser
            mock_load_module.return_value = mock_module_with_browser

            registry = ToolRegistry()
            # Need to clear registry again because clear_tool_registry fixture might run before patch
            registry.clear_registry()

            # Ensure LLMConfig is available for load_llm_tool if any are discovered
            mock_config_fixture.llm = LLMConfig()

            # 4. Call the function under test
            load_and_register_all_tools(registry)

            # 5. Assertions - verify adapted Browser methods are registered
            assert registry.get_tool("browser_click") is not None
            assert registry.get_tool("browser_type") is not None
            assert registry.get_tool("browser_goto") is not None
            assert registry.get_tool("browser_scroll") is not None
            assert len(registry.list_tools()) >= 4 # May have default tools if populate_default_tools runs before clear

            click_tool = registry.get_tool("browser_click")
            type_tool = registry.get_tool("browser_type")
            goto_tool = registry.get_tool("browser_goto")
            scroll_tool = registry.get_tool("browser_scroll")

            assert click_tool.description == "Clicks an element."
            assert "element_id" in click_tool.input_schema

            assert type_tool.description == "Types text into an element."
            assert "element_id" in type_tool.input_schema
            assert "content" in type_tool.input_schema

            # 6. Verify callable wrappers
            # Call the adapted tool function and check if the mock was called
            await click_tool.tool_function(element_id=101)
            MockBrowser.click_mock.assert_called_once_with(101)

            await type_tool.tool_function(element_id=102, content="hello world")
            MockBrowser.type_mock.assert_called_once_with(102, "hello world", False)

            await goto_tool.tool_function(url="https://example.com")
            MockBrowser.goto_mock.assert_called_once_with("https://example.com", 90000)

            await scroll_tool.tool_function(direction="down")
            MockBrowser.scroll_mock.assert_called_once_with("down")
