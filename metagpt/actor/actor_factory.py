from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, Field
import uuid

from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.provider.base_llm import BaseLLM
from metagpt.configs.models_config import ModelsConfig
from metagpt.utils.tool_registry import ToolRegistry, ToolMetadata
from metagpt.utils.knowledge_base import BaseKnowledgeBase, KnowledgeItem
from metagpt.planner.planner import SubTask
from metagpt.actor.actor import Actor # The concrete Actor implementation

class ActorFactory(BaseModel):
    tool_registry: ToolRegistry
    knowledge_base: BaseKnowledgeBase
    default_llm_name_or_type: Optional[str] = None
    # In a real scenario, you might have different LLM configs for different Actor types

    def create_llm_for_actor(self) -> BaseLLM:
        llm_config = ModelsConfig.default().get(self.default_llm_name_or_type)
        if llm_config:
            return create_llm_instance(llm_config)
        # Fallback to a default LLM if not specified or found
        # This needs to be robust, possibly reading from a global config
        raise ValueError("Default LLM not configured for ActorFactory.")

    async def create_actor_for_task(self, sub_task: SubTask) -> Actor:
        actor_id = str(uuid.uuid4())
        actor_name = f"Actor-{sub_task.task_id}"
        actor_description = f"Dynamic Actor for: {sub_task.objective}"

        # 1. LLM Configuration
        actor_llm = self.create_llm_for_actor()

        # 2. Tool Provisioning (Enhanced with LLM for dynamic matching)
        provisioned_tools: Dict[str, ToolMetadata] = {}
        available_tools_desc = "\n".join([f"- {name}: {meta.description}" for name, meta in self.tool_registry.list_tools().items()])

        tool_selection_prompt = f"""Given the sub-task objective: '{sub_task.objective}', and the following available tools:
{available_tools_desc}

Which tool(s) are most relevant for this sub-task? List the tool names, comma-separated. Respond ONLY with tool names or 'NONE' if no tool is relevant.
"""
        # The ActorFactory itself might need an LLM or use the default_llm_name_or_type
        # For simplicity, let's reuse create_llm_for_actor for tool selection for now.
        selection_llm = self.create_llm_for_actor()
        tool_recommendation = await selection_llm.aask(tool_selection_prompt)

        recommended_tool_names = [name.strip() for name in tool_recommendation.split(',') if name.strip() != 'NONE']

        for tool_name in recommended_tool_names:
            tool_meta = self.tool_registry.get_tool(tool_name)
            if tool_meta:
                provisioned_tools[tool_meta.name] = tool_meta

        # 3. Knowledge Contextualization (Simplified: query KB with objective as query)
        contextual_knowledge: List[KnowledgeItem] = []
        if self.knowledge_base:
            # Query the KB for relevant knowledge based on the sub-task objective
            relevant_docs = await self.knowledge_base.query(sub_task.objective, top_k=2)
            contextual_knowledge.extend(relevant_docs)

        actor = Actor(
            actor_id=actor_id,
            name=actor_name,
            description=actor_description,
            llm=actor_llm,
            tools=provisioned_tools,
            knowledge=contextual_knowledge,
            current_sub_task=sub_task # Assign the sub-task to the actor upon creation
        )
        return actor
