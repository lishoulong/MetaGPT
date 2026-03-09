from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
import json
import re

from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message
from metagpt.utils.tool_registry import ToolMetadata
from metagpt.utils.knowledge_base import KnowledgeItem
from metagpt.planner.planner import SubTask

class BaseActor(ABC, BaseModel):
    """Abstract base class for a dynamic Actor."""
    actor_id: str
    name: str
    description: str
    llm: BaseLLM
    tools: Dict[str, ToolMetadata] = Field(default_factory=dict)
    knowledge: List[KnowledgeItem] = Field(default_factory=list)
    current_sub_task: Optional[SubTask] = None

    @abstractmethod
    async def run(self) -> Message:
        """Executes the assigned sub-task using ReAct approach."""
        pass

    def add_tool(self, tool_metadata: ToolMetadata):
        self.tools[tool_metadata.name] = tool_metadata

    def add_knowledge_item(self, item: KnowledgeItem):
        self.knowledge.append(item)


class Actor(BaseActor):
    """A concrete implementation of a dynamic Actor using a simplified ReAct loop."""
    _thought_history: List[str] = Field(default_factory=list)
    _observation_history: List[str] = Field(default_factory=list)
    _scratchpad: str = ""
    _max_react_steps: int = 5 # Limit the number of ReAct steps to prevent infinite loops

    async def run(self) -> Message:
        if not self.current_sub_task:
            return Message(content="No sub-task assigned to Actor.", role="system", sent_from=self.name)

        self._thought_history = []
        self._observation_history = []
        self._scratchpad = ""

        task_objective = self.current_sub_task.objective
        available_tools_desc = "\n".join([
            f"- {name}: {meta.description} (Usage: {meta.usage_example})"
            for name, meta in self.tools.items()
        ])
        knowledge_context = "\n".join([item.content for item in self.knowledge])

        # Initial prompt for the ReAct loop
        initial_prompt = f"""
        You are {self.name}, a {self.description}.
        Your current sub-task is: {task_objective}.

        Relevant Knowledge:
        {knowledge_context or "No specific knowledge provided."}

        Available Tools:
        {available_tools_desc or "No tools available."}

        You must use the following format:
        Thought: you should always think about what to do
        Action: tool_name(arg1='value1', arg2='value2') # Only if you need to use a tool.
        Observation: the result of the action
        ... (this Thought/Action/Observation can repeat N times)
        Thought: I have completed the task.
        Finish: final result of the sub-task

        Begin!
        """

        self._scratchpad += initial_prompt.strip() + "\n"

        for step in range(self._max_react_steps):
            response = await self.llm.aask(self._scratchpad)
            self._scratchpad += response.strip() + "\n"
            self._thought_history.append(response.strip())

            if "Finish:" in response:
                final_result = response.split("Finish:", 1)[1].strip()
                return Message(content=final_result, role="assistant", sent_from=self.name,
                                cause_by=type(self.current_sub_task).__name__) # Assuming SubTask name is good cause_by

            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                args_str = action_match.group(2)

                try:
                    # Safely parse arguments
                    args = {}
                    # Using regex to parse key-value pairs (supports 'key'='value' and 'key'=value for non-strings)
                    # This regex is a bit simplified, a proper parser might be needed for complex cases
                    for arg_pair in re.findall(r"(\w+)\s*=\s*('[^']*'|"[^"]*"|[^,)]+)", args_str):
                        key = arg_pair[0]
                        value = arg_pair[1].strip()
                        if value.startswith("'") and value.endswith("'"):
                            args[key] = value[1:-1]
                        elif value.startswith('"') and value.endswith('"'):
                            args[key] = value[1:-1]
                        else:
                            try:
                                args[key] = json.loads(value) # Try to parse as JSON for numbers, booleans, etc.
                            except json.JSONDecodeError:
                                args[key] = value # Fallback to string if not JSON

                except Exception as e:
                    observation = f"Error parsing action arguments: {e}. Response: {response}"
                    self._scratchpad += f"Observation: {observation}\n"
                    self._observation_history.append(observation)
                    continue

                tool_meta = self.tools.get(tool_name)
                if tool_meta and tool_meta.tool_function:
                    try:
                        tool_result = await tool_meta.tool_function(**args)
                        observation = f"Tool {tool_name} returned: {tool_result}"
                    except Exception as e:
                        observation = f"Error executing tool {tool_name}: {e}"
                else:
                    observation = f"Tool {tool_name} not found or function not callable."
            else:
                observation = "No valid Action found in the LLM response. Please provide a clear Action or Finish."

            self._scratchpad += f"Observation: {observation}\n"
            self._observation_history.append(observation)

        return Message(content=f"Actor {self.name} failed to complete sub-task: {task_objective} within {self._max_react_steps} steps. Last scratchpad:\n{self._scratchpad}",
                       role="system", sent_from=self.name)
