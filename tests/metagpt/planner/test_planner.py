import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from metagpt.planner.planner import Planner, SubTask, TaskGraph
from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message
from metagpt.actor.actor_factory import ActorFactory
from metagpt.utils.tool_registry import ToolRegistry
from metagpt.utils.knowledge_base import SimpleKnowledgeBase

class MockLLM(BaseLLM):
    async def aask(self, msg: str, **kwargs) -> str:
        if "Decompose the following main goal" in msg:
            return json.dumps([
                {"objective": "Design UI mockups", "inputs": {"design_brief": "User stories"}, "outputs": {"ui_mockups": "Image files"}},
                {"objective": "Implement backend API", "inputs": {"api_specs": "JSON/YAML"}, "outputs": {"api_endpoint_code": "Python files"}}
            ])
        return ""

class TestPlanner:
    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def mock_actor_factory(self):
        mock_factory = MagicMock(spec=ActorFactory)
        mock_factory.create_actor_for_task = AsyncMock(return_value=None)
        return mock_factory

    @pytest.fixture
    def planner(self, mock_llm, mock_actor_factory):
        return Planner(llm=mock_llm, goal="Create a web application", actor_factory=mock_actor_factory)

    @pytest.mark.asyncio
    async def test_decompose_task(self, planner):
        sub_tasks = await planner.decompose_task("Create a web application")
        assert len(sub_tasks) == 2
        assert sub_tasks[0].objective == "Design UI mockups"
        assert sub_tasks[1].objective == "Implement backend API"
        assert sub_tasks[0].status == "pending"

    @pytest.mark.asyncio
    async def test_add_sub_task(self, planner):
        sub_task = SubTask(task_id="test-task-1", objective="Test objective")
        planner.add_sub_task(sub_task)
        assert "test-task-1" in planner.task_graph.tasks
        assert planner.task_graph.tasks["test-task-1"] == sub_task

    @pytest.mark.asyncio
    async def test_update_task_status(self, planner):
        sub_task = SubTask(task_id="test-task-2", objective="Test objective")
        planner.add_sub_task(sub_task)
        planner.update_task_status("test-task-2", "in_progress", "actor-123")
        assert planner.task_graph.tasks["test-task-2"].status == "in_progress"
        assert planner.task_graph.tasks["test-task-2"].assigned_actor_id == "actor-123"

    @pytest.mark.asyncio
    async def test_adjust_task_graph_completed(self, planner):
        sub_task = SubTask(task_id="app-1-1", objective="Design UI mockups", status="in_progress")
        planner.add_sub_task(sub_task)
        feedback_message = Message(content="app-1-1:completed:UI mockups are done", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        assert planner.task_graph.tasks["app-1-1"].status == "completed"

    @pytest.mark.asyncio
    async def test_adjust_task_graph_failed(self, planner):
        sub_task = SubTask(task_id="app-1-2", objective="Implement backend API", status="in_progress")
        planner.add_sub_task(sub_task)
        feedback_message = Message(content="app-1-2:failed:API implementation failed due to X", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        assert planner.task_graph.tasks["app-1-2"].status == "failed"

    @pytest.mark.asyncio
    async def test_adjust_task_graph_blocked(self, planner):
        sub_task = SubTask(task_id="app-1-3", objective="Set up database", status="in_progress")
        planner.add_sub_task(sub_task)
        feedback_message = Message(content="app-1-3:blocked:Waiting for infra setup", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        assert planner.task_graph.tasks["app-1-3"].status == "blocked"

    @pytest.mark.asyncio
    async def test_adjust_task_graph_new_observation(self, planner, capsys):
        sub_task = SubTask(task_id="app-1-4", objective="Gather user requirements", status="in_progress")
        planner.add_sub_task(sub_task)
        feedback_message = Message(content="app-1-4:new_observation:User feedback collected", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        # For new_observation, currently just prints, no status change.
        assert planner.task_graph.tasks["app-1-4"].status == "in_progress" # Should remain in_progress
        captured = capsys.readouterr()
        assert "New observation for task app-1-4: User feedback collected" in captured.out

    @pytest.mark.asyncio
    async def test_adjust_task_graph_unknown_task(self, planner, capsys):
        feedback_message = Message(content="unknown-task:completed:some result", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        captured = capsys.readouterr()
        assert "Feedback for unknown task_id: unknown-task" in captured.out

    @pytest.mark.asyncio
    async def test_adjust_task_graph_invalid_format(self, planner, capsys):
        feedback_message = Message(content="invalid-format", role="assistant")
        await planner.adjust_task_graph(feedback_message)
        captured = capsys.readouterr()
        assert "Invalid feedback format: invalid-format" in captured.out

    @pytest.mark.asyncio
    async def test_delegate_task(self, planner, mock_actor_factory):
        sub_task = SubTask(task_id="app-1-5", objective="Perform a task")
        planner.add_sub_task(sub_task)

        # Configure mock actor factory to return a mock actor
        mock_actor = MagicMock()
        mock_actor.actor_id = "mock-actor-id"
        mock_actor_factory.create_actor_for_task.return_value = mock_actor

        actor = await planner.delegate_task("app-1-5")

        mock_actor_factory.create_actor_for_task.assert_called_once_with(sub_task)
        assert actor == mock_actor
        assert planner.task_graph.tasks["app-1-5"].status == "in_progress"
        assert planner.task_graph.tasks["app-1-5"].assigned_actor_id == "mock-actor-id"

    @pytest.mark.asyncio
    async def test_delegate_task_already_in_progress(self, planner, mock_actor_factory):
        sub_task = SubTask(task_id="app-1-6", objective="Already in progress", status="in_progress")
        planner.add_sub_task(sub_task)

        actor = await planner.delegate_task("app-1-6")

        mock_actor_factory.create_actor_for_task.assert_not_called()
        assert actor is None

