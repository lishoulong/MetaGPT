from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from metagpt.provider.base_llm import BaseLLM
from metagpt.schema import Message
from metagpt.actor.actor_factory import ActorFactory
from metagpt.actor.actor import Actor

class SubTask(BaseModel):
    task_id: str
    objective: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending" # pending, in_progress, completed, failed, blocked
    assigned_actor_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)

class TaskGraph(BaseModel):
    tasks: Dict[str, SubTask] = Field(default_factory=dict)
    # Graph structure could be more complex, e.g., adjacency list

class Planner(BaseModel):
    llm: BaseLLM
    goal: str
    task_graph: TaskGraph = Field(default_factory=TaskGraph)
    current_task_id: Optional[str] = None
    actor_factory: ActorFactory # Added actor_factory

    def add_sub_task(self, sub_task: SubTask):
        self.task_graph.tasks[sub_task.task_id] = sub_task

    def update_task_status(self, task_id: str, status: str, actor_id: Optional[str] = None):
        if task_id in self.task_graph.tasks:
            self.task_graph.tasks[task_id].status = status
            if actor_id:
                self.task_graph.tasks[task_id].assigned_actor_id = actor_id

    async def decompose_task(self, main_goal: str) -> List[SubTask]:
        system_prompt = """You are an expert task decomposer. Your goal is to break down a main goal into a list of smaller, actionable sub-tasks.
        Each sub-task should be clearly defined with an objective, expected inputs, and expected outputs.
        Respond ONLY with a JSON array of sub-task objects, where each object has the keys 'objective', 'inputs', and 'outputs'.
        Example:
        [
            {"objective": "Design UI mockups", "inputs": {"design_brief": "User stories"}, "outputs": {"ui_mockups": "Image files"}},
            {"objective": "Implement backend API", "inputs": {"api_specs": "JSON/YAML"}, "outputs": {"api_endpoint_code": "Python files"}}
        ]
        """
        user_prompt = f"""Decompose the following main goal into sub-tasks: {main_goal}
        """

        response_str = await self.llm.aask(user_prompt, system_msgs=[system_prompt])

        import json
        sub_task_dicts = json.loads(response_str)

        sub_tasks = []
        for idx, task_dict in enumerate(sub_task_dicts):
            sub_tasks.append(SubTask(task_id=f"{self.goal}-{idx+1}", **task_dict))

        return sub_tasks

    async def delegate_task(self, sub_task_id: str) -> Optional[Actor]:
        if sub_task_id not in self.task_graph.tasks:
            return None
        sub_task = self.task_graph.tasks[sub_task_id]
        if sub_task.status != "pending":
            return None # Task already delegated or in progress

        actor = await self.actor_factory.create_actor_for_task(sub_task)
        self.update_task_status(sub_task_id, "in_progress", actor.actor_id)
        return actor

    async def adjust_task_graph(self, feedback: Message):
        # For this initial implementation, we'll update task status based on feedback content.
        # A more advanced version would involve LLM re-planning.
        # Assume feedback content is structured, e.g., "TASK_ID:STATUS:DETAILS"
        feedback_parts = feedback.content.split(':', 2)
        if len(feedback_parts) < 2:
            print(f"Invalid feedback format: {feedback.content}")
            return

        task_id = feedback_parts[0]
        new_status = feedback_parts[1]
        details = feedback_parts[2] if len(feedback_parts) == 3 else ""

        if task_id in self.task_graph.tasks:
            sub_task = self.task_graph.tasks[task_id]
            print(f"Planner received feedback for task {task_id}: {new_status} - {details}")

            if new_status == "completed":
                self.update_task_status(task_id, "completed", sub_task.assigned_actor_id)
                # Here, we could also check dependencies and make next tasks ready
            elif new_status == "failed":
                self.update_task_status(task_id, "failed", sub_task.assigned_actor_id)
                # LLM could be used here to re-plan or generate an alternative approach
            elif new_status == "blocked":
                self.update_task_status(task_id, "blocked", sub_task.assigned_actor_id)
                # LLM could be used to suggest unblocking actions or assign to another actor
            elif new_status == "new_observation":
                print(f"New observation for task {task_id}: {details}")
                # LLM could be used to evaluate observation and adjust future tasks
            else:
                print(f"Unknown status in feedback: {new_status}")
        else:
            print(f"Feedback for unknown task_id: {task_id}")

    @property
    def current_task(self) -> Optional[SubTask]:
        if self.current_task_id and self.current_task_id in self.task_graph.tasks:
            return self.task_graph.tasks[self.current_task_id]
        return None
