
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from typing import Literal

from metagpt.planner.planner import Planner, SubTask
from metagpt.actor.actor_factory import ActorFactory
from metagpt.actor.actor import Actor
from metagpt.utils.tool_registry import ToolRegistry, ToolMetadata, populate_default_tools, load_and_register_all_tools
from metagpt.configs.llm_config import LLMConfig
from pathlib import Path
from metagpt.utils.knowledge_base import SimpleKnowledgeBase, KnowledgeItem
from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message
from metagpt.tools.tool_data_type import Tool # For mock Tool

# Import _load_module_from_path for patching
from metagpt.utils.tool_loader import _load_module_from_path

# --- Mock LLM for Planner and Actor (adapted from test_dynamic_workflow.py) ---
class MockIntegrationLLM(BaseLLM):
    def __init__(self, planner_responses: list, actor_responses: dict):
        super().__init__()
        self._planner_responses = planner_responses
        self._actor_responses = actor_responses
        self._planner_call_count = 0
        self._actor_call_counts = {}

    async def aask(self, msg: str, **kwargs) -> str:
        if "Decompose the following main goal" in msg:
            if self._planner_call_count < len(self._planner_responses):
                response = self._planner_responses[self._planner_call_count]
                self._planner_call_count += 1
                return response
            return json.dumps([{"objective": "Fallback task", "inputs": {}, "outputs": {}}])

        # Actor's ReAct loop LLM calls
        if "Begin!" in msg or "Thought:" in msg or "Observation:" in msg:
            actor_name = "UnknownActor" # A bit hacky, but for test purpose
            for actor_key in self._actor_responses.keys():
                if actor_key in msg: # Try to guess which actor is calling
                    actor_name = actor_key
                    break

            if actor_name not in self._actor_call_counts:
                self._actor_call_counts[actor_name] = 0

            responses = self._actor_responses.get(actor_name, [])
            if self._actor_call_counts[actor_name] < len(responses):
                response = responses[self._actor_call_counts[actor_name]]
                self._actor_call_counts[actor_name] += 1
                return response
            return "Finish: Actor exhausted responses."

        if "Which tool(s) are most relevant" in msg:
            # For this test, we expect the LLM to choose specific browser tools
            if "browser_goto" in msg: # Check if browser_goto is in the prompt for selection
                return "browser_goto"
            elif "browser_type" in msg:
                return "browser_type"
            elif "browser_scroll" in msg:
                return "browser_scroll"
            return "NONE" # Fallback if no specific browser tool is requested by the prompt

        return ""

    def get_choice(self, prompt: str, choices: list[str], **kwargs) -> str:
        return choices[0] # Simplified for now

# --- Fixtures ---
@pytest.fixture(autouse=True)
def mock_config_fixture():
    with patch('metagpt.config2.config') as mock_cfg:
        mock_cfg.llm = LLMConfig()  # Provide a default LLMConfig
        mock_cfg.tool_dirs = []  # Default to empty for controlled tests
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
def mock_browser_env():
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
        def __init__(self, **data):
            pass

        async def start(self):
            self.playwright = mock_playwright
            self.browser_instance = mock_browser_instance
            self.page = mock_page
            return "started"

        async def stop(self):
            self.playwright = None
            return "stopped"

        async def click(self, element_id: int):
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

        async def _wait_page(self):
            return f"SUCCESS, URL: {mock_page.url} have been loaded."

    # 2. Mock the old Tool object for Browser
    mock_old_browser_tool = MagicMock(spec=Tool)
    mock_old_browser_tool.name = "Browser"
    mock_old_browser_tool.path = "/metagpt/tools/libs/browser.py" # Dummy path
    mock_old_browser_tool.schemas = {
        "class_name": "Browser",
        "include_functions": ["click", "type", "goto", "scroll"],
        "methods": {
            "click": {"description": "Clicks an element.", "parameters": {"element_id": {"type": "integer"}}, "returns": {"type": "string"}},
            "type": {"description": "Types text into an element.", "parameters": {"element_id": {"type": "integer"}, "content": {"type": "string"}}, "returns": {"type": "string"}},
            "goto": {"description": "Navigates to a URL.", "parameters": {"url": {"type": "string"}}, "returns": {"type": "string"}},
            "scroll": {"description": "Scrolls the page.", "parameters": {"direction": {"type": "string", "enum": ["down", "up"]}}, "returns": {"type": "string"}}
        }
    }

    # Patch OLD_TOOL_REGISTRY and _load_module_from_path
    with patch('metagpt.tools.tool_registry.TOOL_REGISTRY', {"Browser": mock_old_browser_tool}), \
         patch('metagpt.utils.tool_loader._load_module_from_path') as mock_load_module, \
         patch('metagpt.utils.a11y_tree.click_element', AsyncMock()), \
         patch('metagpt.utils.a11y_tree.type_text', AsyncMock()), \
         patch('metagpt.utils.a11y_tree.scroll_page', AsyncMock()), \
         patch('metagpt.utils.a11y_tree.get_accessibility_tree', AsyncMock(return_value=[])), \
         patch('metagpt.utils.report.BrowserReporter', MagicMock()):

        mock_module_with_browser = MagicMock()
        mock_module_with_browser.Browser = MockBrowser
        mock_load_module.return_value = mock_module_with_browser

        # Ensure LLMConfig is available
        mock_config = MagicMock()
        mock_config.llm = LLMConfig()
        with patch('metagpt.config2.config', mock_config):
            # Populate the ToolRegistry with adapted tools
            registry = ToolRegistry()
            registry.clear_registry()
            load_and_register_all_tools(registry)
            yield registry, MockBrowser

# --- Test Case ---
@pytest.mark.asyncio
async def test_actor_uses_adapted_browser_tool(mock_browser_env):
    tool_registry, MockBrowser = mock_browser_env

    # 1. Mock LLM responses for the Actor
    actor_llm_responses = {
        "Researcher": [
            # First, the Actor decides to navigate
            "Thought: I need to open a specific webpage to start my research. Action: browser_goto(url='https://example.com/research')",
            # Then, it might type something
            "Thought: Now that I\'m on the page, I need to type a query into a search box. Action: browser_type(element_id=10, content='MetaGPT project')",
            # Finally, it scrolls to see more content
            "Thought: I have typed the query, now I will scroll down to see more results. Action: browser_scroll(direction='down')",
            "Finish: Research completed using browser."
        ]
    }

    mock_llm = MockIntegrationLLM(planner_responses=[], actor_responses=actor_llm_responses)

    # 2. Mock ModelsConfig.default().get and create_llm_instance for ActorFactory
    mock_llm_config = MagicMock()
    mock_llm_config.model = "mock-llm-model"

    with patch("metagpt.configs.models_config.ModelsConfig.default", lambda: MagicMock(get=lambda x: mock_llm_config)), \
         patch("metagpt.provider.llm_provider_registry.create_llm_instance", lambda x: mock_llm):

        # Initialize ActorFactory
        actor_factory = ActorFactory(
            tool_registry=tool_registry,
            knowledge_base=SimpleKnowledgeBase(), # Not strictly needed for this test but good practice
            default_llm_name_or_type="mock-llm-model"
        )

        # Create a mock Role and Actor that uses the ActorFactory
        mock_role = MagicMock()
        mock_role.name = "Researcher"
        mock_role.profile = "Researcher"
        mock_role.desc = "Conducts web research using browser tools."
        mock_role.use_tools = True
        mock_role.llm = mock_llm # Assign the mock_llm to the role

        actor = Actor(llm=mock_llm, name=mock_role.name, profile=mock_role.profile, goal=mock_role.desc)
        actor.set_tool_code_block_processor(actor_factory.tool_code_block_processor)

        # 3. Simulate the Actor's run method
        await actor.run(Message(content="Conduct web research on MetaGPT."))

        # 4. Assert tool calls on the MockBrowser
        MockBrowser.goto_mock.assert_called_once_with("https://example.com/research", 90000)
        MockBrowser.type_mock.assert_called_once_with(10, "MetaGPT project", False)
        MockBrowser.scroll_mock.assert_called_once_with("down")
