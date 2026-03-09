import pytest
from unittest.mock import AsyncMock, MagicMock

from metagpt.actor.actor_factory import ActorFactory
from metagpt.planner.planner import SubTask
from metagpt.provider.base_llm import BaseLLM
from metagpt.utils.tool_registry import ToolRegistry, ToolMetadata, populate_default_tools
from metagpt.utils.knowledge_base import SimpleKnowledgeBase, KnowledgeItem
from metagpt.actor.actor import Actor

# Mock implementations for dependencies
class MockLLM(BaseLLM):
    async def aask(self, msg: str, **kwargs) -> str:
        if "Which tool(s) are most relevant" in msg:
            if "UI" in msg:
                return "example_search"
            return "NONE"
        return ""

@pytest.fixture
def mock_tool_registry():
    registry = ToolRegistry()
    populate_default_tools(registry) # Adds 'example_search'
    return registry

@pytest.fixture
def mock_knowledge_base():
    kb = SimpleKnowledgeBase()
    # Add some dummy knowledge
    kb.add_knowledge(KnowledgeItem(id="k1", content="UI design principles"))
    kb.add_knowledge(KnowledgeItem(id="k2", content="Backend API best practices"))
    return kb

@pytest.fixture
def mock_llm_factory():
    # This mock LLM is used by ActorFactory to create LLMs for actors and for tool selection
    return MockLLM()

@pytest.fixture
def actor_factory(mock_tool_registry, mock_knowledge_base, mock_llm_factory):
    # The ActorFactory needs a way to create LLM instances; we'll mock ModelsConfig
    # to return a dummy LLMConfig when get() is called.
    mock_llm_config = MagicMock()
    mock_llm_config.model = "mock-llm-model"

    with pytest.MonkeyPatch.context() as m:
        m.setattr("metagpt.configs.models_config.ModelsConfig.default", lambda: MagicMock(get=lambda x: mock_llm_config))
        m.setattr("metagpt.provider.llm_provider_registry.create_llm_instance", lambda x: mock_llm_factory)
        yield ActorFactory(
            tool_registry=mock_tool_registry,
            knowledge_base=mock_knowledge_base,
            default_llm_name_or_type="mock-llm-model"
        )

@pytest.mark.asyncio
class TestActorFactory:
    async def test_create_llm_for_actor(self, actor_factory, mock_llm_factory):
        llm_instance = actor_factory.create_llm_for_actor()
        assert llm_instance == mock_llm_factory

    async def test_create_actor_for_task_no_tools(self, actor_factory, mock_llm_factory):
        sub_task = SubTask(task_id="task-123", objective="Implement a simple login feature")
        mock_llm_factory.aask.return_value = "NONE" # No tools recommended

        actor = await actor_factory.create_actor_for_task(sub_task)

        assert isinstance(actor, Actor)
        assert actor.name == "Actor-task-123"
        assert actor.current_sub_task == sub_task
        assert actor.tools == {}
        assert len(actor.knowledge) > 0 # Should get some knowledge from KB
        assert "UI design principles" in actor.knowledge[0].content or "Backend API best practices" in actor.knowledge[0].content

    async def test_create_actor_for_task_with_tools(self, actor_factory, mock_llm_factory, mock_tool_registry):
        sub_task = SubTask(task_id="task-456", objective="Design UI mockups for the landing page")
        mock_llm_factory.aask.return_value = "example_search" # Mock LLM recommends this tool

        actor = await actor_factory.create_actor_for_task(sub_task)

        assert isinstance(actor, Actor)
        assert actor.name == "Actor-task-456"
        assert actor.current_sub_task == sub_task
        assert "example_search" in actor.tools
        assert actor.tools["example_search"] == mock_tool_registry.get_tool("example_search")
        assert len(actor.knowledge) > 0

    async def test_create_actor_for_task_multiple_tools(self, actor_factory, mock_llm_factory, mock_tool_registry):
        # For this test, let's add another dummy tool to the registry
        mock_tool_registry.register_tool(ToolMetadata(
            name="dummy_tool",
            description="A dummy tool.",
            usage_example="dummy_tool()",
            tool_function=lambda: "dummy_result"
        ))

        sub_task = SubTask(task_id="task-789", objective="Perform research and then summarize findings")
        mock_llm_factory.aask.return_value = "example_search, dummy_tool" # Mock LLM recommends multiple tools

        actor = await actor_factory.create_actor_for_task(sub_task)

        assert isinstance(actor, Actor)
        assert actor.name == "Actor-task-789"
        assert "example_search" in actor.tools
        assert "dummy_tool" in actor.tools
        assert actor.tools["example_search"] == mock_tool_registry.get_tool("example_search")
        assert actor.tools["dummy_tool"] == mock_tool_registry.get_tool("dummy_tool")

    async def test_create_actor_for_task_invalid_llm_config(self, mock_tool_registry, mock_knowledge_base):
        with pytest.MonkeyPatch.context() as m:
            m.setattr("metagpt.configs.models_config.ModelsConfig.default", lambda: MagicMock(get=lambda x: None))
            m.setattr("metagpt.provider.llm_provider_registry.create_llm_instance", lambda x: MockLLM())
            factory = ActorFactory(
                tool_registry=mock_tool_registry,
                knowledge_base=mock_knowledge_base,
                default_llm_name_or_type="non-existent-llm"
            )
            sub_task = SubTask(task_id="task-fail", objective="fail task")
            with pytest.raises(ValueError, match="Default LLM not configured for ActorFactory."):
                await factory.create_actor_for_task(sub_task)
