import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from metagpt.actor.actor import Actor, BaseActor
from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message
from metagpt.planner.planner import SubTask
from metagpt.utils.tool_registry import ToolMetadata
from metagpt.utils.knowledge_base import KnowledgeItem

# Mock implementations for dependencies
class MockLLM(BaseLLM):
    def __init__(self, responses: list):
        super().__init__()
        self._responses = responses
        self._call_count = 0

    async def aask(self, msg: str, **kwargs) -> str:
        if self._call_count < len(self._responses):
            response = self._responses[self._call_count]
            self._call_count += 1
            return response
        return "Finish: Unexpected call to LLM after all responses exhausted."

    def get_choice(self, prompt: str, choices: list[str], **kwargs) -> str:
        return choices[0] # Simplified for now

@pytest.fixture
def mock_sub_task():
    return SubTask(task_id="test-task-1", objective="Summarize the given text using a tool.")

@pytest.fixture
def mock_knowledge():
    return [KnowledgeItem(id="k1", content="Some background knowledge.")]

def mock_summarize_tool(text: str) -> str:
    return f"Summary of: {text[:20]}..."

def mock_translate_tool(text: str, target_lang: str) -> str:
    return f"Translated '{text}' to {target_lang}."

@pytest.fixture
def mock_tools():
    return {
        "summarize_tool": ToolMetadata(
            name="summarize_tool",
            description="Summarizes text.",
            usage_example="summarize_tool(text='long text')",
            input_schema={"text": {"type": "string"}},
            tool_function=mock_summarize_tool
        ),
        "translate_tool": ToolMetadata(
            name="translate_tool",
            description="Translates text to a target language.",
            usage_example="translate_tool(text='hello', target_lang='fr')",
            input_schema={"text": {"type": "string"}, "target_lang": {"type": "string"}},
            tool_function=mock_translate_tool
        ),
    }

@pytest.mark.asyncio
class TestActorReActLoop:
    async def test_react_loop_success(self, mock_sub_task, mock_knowledge, mock_tools):
        # Simulate a successful ReAct loop
        llm_responses = [
            "Thought: I need to summarize the text. I will use the summarize_tool.\nAction: summarize_tool(text='This is a long piece of text to be summarized.')",
            "Thought: I have summarized the text. The task is complete.\nFinish: Text successfully summarized."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a1",
            name="Summarizer",
            description="Summarizes documents.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()

        assert result.content == "Text successfully summarized."
        assert result.role == "assistant"
        assert "summarize_tool" in actor._scratchpad # Check if tool was used
        assert "Summary of: This is a long pie..." in actor._scratchpad # Check observation

    async def test_react_loop_tool_not_found(self, mock_sub_task, mock_knowledge, mock_tools):
        llm_responses = [
            "Thought: I need to use a tool that does not exist.\nAction: non_existent_tool(text='some text')",
            "Thought: The tool was not found. I need to finish now.\nFinish: Failed due to unknown tool."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a2",
            name="FaultyActor",
            description="Tries to use wrong tools.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Failed due to unknown tool."
        assert "non_existent_tool not found" in actor._scratchpad

    async def test_react_loop_tool_execution_error(self, mock_sub_task, mock_knowledge, mock_tools):
        def failing_tool(text: str):
            raise ValueError("Tool failed internally")

        mock_tools["failing_tool"] = ToolMetadata(
            name="failing_tool",
            description="A tool that always fails.",
            tool_function=failing_tool
        )

        llm_responses = [
            "Thought: I will use the failing tool.\nAction: failing_tool(text='input')",
            "Thought: The tool failed. I need to report this.\nFinish: Tool execution failed."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a3",
            name="ErrorHandler",
            description="Handles errors.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Tool execution failed."
        assert "Error executing tool failing_tool: Tool failed internally" in actor._scratchpad

    async def test_react_loop_max_steps_exceeded(self, mock_sub_task, mock_knowledge, mock_tools):
        # LLM never reaches a Finish step
        llm_responses = [
            "Thought: Step 1.\nAction: summarize_tool(text='a')",
            "Thought: Step 2.\nAction: summarize_tool(text='b')",
            "Thought: Step 3.\nAction: summarize_tool(text='c')",
            "Thought: Step 4.\nAction: summarize_tool(text='d')",
            "Thought: Step 5.\nAction: summarize_tool(text='e')",
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a4",
            name="InfiniteActor",
            description="Never finishes.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )
        actor._max_react_steps = 5 # Set a small limit for testing

        result = await actor.run()
        assert "failed to complete sub-task" in result.content
        assert result.role == "system" # System role indicates failure/issue
        assert len(actor._thought_history) == actor._max_react_steps

    async def test_react_loop_invalid_action_format(self, mock_sub_task, mock_knowledge, mock_tools):
        llm_responses = [
            "Thought: I will try an invalid action format.\nAction: summarize_tool text 'some text'", # Invalid format
            "Thought: I realized my mistake.\nFinish: Task completed despite initial error."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a5",
            name="FormatterActor",
            description="Learns from mistakes.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Task completed despite initial error."
        assert "No valid Action found in the LLM response" in actor._scratchpad

    async def test_react_loop_no_action_then_finish(self, mock_sub_task, mock_knowledge):
        llm_responses = [
            "Thought: I don't need any tools for this simple task.\nFinish: Directly finished without tools."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a6",
            name="SimpleActor",
            description="Does simple tasks.",
            llm=mock_llm,
            tools={},
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Directly finished without tools."
        assert len(actor._thought_history) == 1
        assert "Action:" not in actor._scratchpad

    async def test_react_loop_complex_args(self, mock_sub_task, mock_knowledge, mock_tools):
        llm_responses = [
            "Thought: I need to translate a complex phrase.\nAction: translate_tool(text='Hello World', target_lang='fr')",
            "Thought: Translation complete.\nFinish: Translated successfully."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a7",
            name="Translator",
            description="Translates.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Translated successfully."
        assert "Translated 'Hello World' to fr." in actor._scratchpad

    async def test_react_loop_args_with_spaces_and_quotes(self, mock_sub_task, mock_knowledge, mock_tools):
        llm_responses = [
            "Thought: I need to translate a phrase with spaces.\nAction: translate_tool(text=\"This is a phrase\", target_lang='es')",
            "Thought: Translation complete.\nFinish: Translated successfully with spaces."
        ]
        mock_llm = MockLLM(llm_responses)

        actor = Actor(
            actor_id="a8",
            name="TranslatorWithSpaces",
            description="Translates.",
            llm=mock_llm,
            tools=mock_tools,
            knowledge=mock_knowledge,
            current_sub_task=mock_sub_task
        )

        result = await actor.run()
        assert result.content == "Translated successfully with spaces."
        assert "Translated 'This is a phrase' to es." in actor._scratchpad
