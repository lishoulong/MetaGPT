import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from metagpt.planner.planner import Planner, SubTask
from metagpt.actor.actor_factory import ActorFactory
from metagpt.actor.actor import Actor
from metagpt.utils.tool_registry import ToolRegistry, ToolMetadata, populate_default_tools, load_and_register_all_tools
from metagpt.configs.llm_config import LLMConfig
from pathlib import Path
from metagpt.utils.knowledge_base import SimpleKnowledgeBase, KnowledgeItem
from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message

# Mock LLM for Planner and Actor
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
            if "Python callable tool" in msg:
                return "python_integration_tool"
            elif "LLM-prompt-based tool" in msg:
                return "llm_integration_tool"
            return "NONE"


        return ""

    def get_choice(self, prompt: str, choices: list[str], **kwargs) -> str:
        return choices[0] # Simplified for now


def mock_design_tool(design_brief: str) -> str:
    return f"UI mockups created for: {design_brief}"

def mock_code_tool(api_specs: str) -> str:
    return f"Backend API implemented for: {api_specs}"

@pytest.fixture(autouse=True)
def mock_config_fixture():
    with patch('metagpt.config2.config') as mock_cfg:
        mock_cfg.llm = LLMConfig()  # Provide a default LLMConfig
        mock_cfg.tool_dirs = []  # Default to empty for controlled tests
        yield mock_cfg

@pytest.fixture
def temp_integration_tool_discovery_env(tmp_path, mock_config_fixture):
    """Sets up a temporary environment for tool discovery for integration tests."""
    tool_dir = tmp_path / "my_integration_tools"
    tool_dir.mkdir()

    # Python tool
    python_tool_file = tool_dir / "my_python_integration_tool.py"
    python_tool_file.write_text("""
from metagpt.utils.tool_registry import ToolMetadata
from typing import Dict, Any

def python_integration_tool(arg: str) -> Dict[str, Any]:
    \"\"\"
    ```json
    {
        \"name\": \"python_integration_tool\",
        \"description\": \"A Python callable tool for integration testing.\",
        \"input_schema\": {\"arg\": {\"type\": \"string\"}},
        \"output_schema\": {\"result\": {\"type\": \"string\"}}
    }
    ```
    This is an integration python tool.
    \"\"\"
    return {\"result\": f\"Python integration tool processed: {arg}\"}
""")

    # LLM tool
    llm_integration_tool_dir = tool_dir / "my_llm_integration_tool"
    llm_integration_tool_dir.mkdir()
    (llm_integration_tool_dir / "config.json").write_text("""
{
    \"name\": \"llm_integration_tool\",
    \"description\": \"An LLM-prompt-based tool for integration testing.\",
    \"input_schema\": {\"query\": {\"type\": \"string\"}},
    \"usage_example\": \"llm_integration_tool(query=\'hello\')\"\
}
""")
    (llm_integration_tool_dir / "prompt.txt").write_text("Generate an integration response for: {query}")

    mock_config_fixture.tool_dirs = [tool_dir]
    yield tool_dir


@pytest.fixture
def setup_integration_env(temp_integration_tool_discovery_env):
    # 1. Setup ToolRegistry
    tool_registry = ToolRegistry()
    tool_registry.clear_registry() # Ensure a clean slate

    # Dynamically load tools using the tool_loader
    load_and_register_all_tools(tool_registry)

    # 2. Setup KnowledgeBase
    knowledge_base = SimpleKnowledgeBase()
    knowledge_base.add_knowledge(KnowledgeItem(id="kb-ui", content="UI design patterns"))
    knowledge_base.add_knowledge(KnowledgeItem(id="kb-api", content="REST API guidelines"))

    return tool_registry, knowledge_base


@pytest.mark.asyncio
async def test_full_dynamic_workflow(setup_integration_env):
    tool_registry, knowledge_base = setup_integration_env

    # Mock LLM responses for Planner and Actors
    planner_llm_responses = [
        json.dumps([
            {"objective": "Design UI mockups", "inputs": {"design_brief": "User stories"}, "outputs": {"ui_mockups": "Image files"}},
            {"objective": "Implement backend API", "inputs": {"api_specs": "JSON/YAML"}, "outputs": {"api_endpoint_code": "Python files"}}
        ])
    ]

    actor_llm_responses = {
        "Actor-Create a web application-1": [
            "Thought: I need to use the Python integration tool. Action: python_integration_tool(arg='initial input')",
            "Thought: Python tool used successfully. Now I will use the LLM integration tool. Action: llm_integration_tool(query='follow-up query')",
            "Thought: All integration steps are complete. Finish: Integration workflow finished."
        ]
    }

    mock_llm = MockIntegrationLLM(planner_llm_responses, actor_llm_responses)

    # Mock ModelsConfig.default().get and create_llm_instance for ActorFactory
    mock_llm_config = MagicMock()
    mock_llm_config.model = "mock-llm-model"

    with pytest.MonkeyPatch.context() as m:
        m.setattr("metagpt.configs.models_config.ModelsConfig.default", lambda: MagicMock(get=lambda x: mock_llm_config))
        m.setattr("metagpt.provider.llm_provider_registry.create_llm_instance", lambda x: mock_llm) # Use the same mock LLM

        # Initialize ActorFactory
        actor_factory = ActorFactory(
            tool_registry=tool_registry,
            knowledge_base=knowledge_base,
            default_llm_name_or_type="mock-llm-model"
        )

        # Initialize Planner
        main_goal = "Create a web application"
        planner = Planner(llm=mock_llm, goal=main_goal, actor_factory=actor_factory)

        # Decompose initial task
        initial_sub_tasks = await planner.decompose_task(main_goal)
        for task in initial_sub_tasks:
            planner.add_sub_task(task)

        # Dynamic Execution Loop
        processed_tasks = 0
        max_iterations = 10

        while True and processed_tasks < max_iterations:
            # Simplified loop for this test: just get the first pending task
            next_task_id = None
            for task_id, task in planner.task_graph.tasks.items():
                if task.status == "pending":
                    next_task_id = task_id
                    break

            if not next_task_id:
                if all(t.status == "completed" for t in planner.task_graph.tasks.values()):
                    break # All tasks completed
                else:
                    break # No pending tasks, but not all completed (e.g., blocked)

            sub_task_to_delegate = planner.task_graph.tasks[next_task_id]

            # Manually set task ID for actor_llm_responses to match the single actor for simplicity
            sub_task_to_delegate.task_id = "Create a web application-1"

            actor = await planner.delegate_task(sub_task_to_delegate.task_id)

            assert actor is not None, f"Actor should be created for task {next_task_id}"
            result_message = await actor.run()

            feedback_content = f"{sub_task_to_delegate.task_id}:completed:{result_message.content}"
            feedback_message = Message(content=feedback_content, role="system", sent_from=actor.name)

            await planner.adjust_task_graph(feedback_message)
            processed_tasks += 1

    # Assertions for dynamic tool usage
    python_tool = tool_registry.get_tool("python_integration_tool")
    assert python_tool is not None
    llm_tool = tool_registry.get_tool("llm_integration_tool")
    assert llm_tool is not None

    # Verify that the mock LLM for the actor was called correctly for tool selection/usage
    mock_llm.aask.assert_any_call("Which tool(s) are most relevant to Python callable tool?")
    mock_llm.aask.assert_any_call("Which tool(s) are most relevant to LLM-prompt-based tool?")

    # Check if the tools were actually invoked via the mock LLM's responses
    # The actor_llm_responses are designed to simulate the calls and their results.
    # We need to check the effect of those simulated calls.
    assert "Python integration tool processed: initial input" in actor.rc.history.get_by_content("Python integration tool processed")[-1].content
    assert "LLM response for prompt_input." in actor.rc.history.get_by_content("LLM response for prompt_input.")[-1].content

    assert planner.task_graph.tasks["Create a web application-1"].status == "completed"
    assert all(t.status == "completed" for t in planner.task_graph.tasks.values())