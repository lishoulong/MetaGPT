import asyncio
from pathlib import Path

import asyncio
from pathlib import Path

import typer

from metagpt.const import CONFIG_ROOT
from metagpt.planner.planner import Planner, SubTask # Added
from metagpt.actor.actor_factory import ActorFactory # Added
from metagpt.utils.tool_registry import ToolRegistry, populate_default_tools # Added
from metagpt.utils.knowledge_base import SimpleKnowledgeBase # Added
from metagpt.provider.llm_provider_registry import create_llm_instance # Added
from metagpt.configs.models_config import ModelsConfig # Added
from metagpt.configs.llm_config import LLMConfig # Added
from metagpt.schema import Message # Moved to top-level

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

def generate_repo(
    idea,
    investment=3.0,
    n_round=5,
    code_review=True,
    implement=True,
    project_name="",
    inc=False,
    project_path="",
    reqa_file="",
    max_auto_summarize_code=0,
    recover_path=None,
    run_tests=False, # Moved to end to match original signature after previous change
):
    """Run the startup logic. Can be called from CLI or other Python scripts."""
    from metagpt.config2 import config
    from metagpt.context import Context
    from metagpt.logs import logger # Added

    config.update_via_cli(project_path, project_name, inc, reqa_file, max_auto_summarize_code)
    ctx = Context(config=config)

    if not recover_path:
        # --- NEW DYNAMIC AGENT WORKFLOW --- START
        # 1. Setup ToolRegistry
        tool_registry = ToolRegistry()
        populate_default_tools(tool_registry) # Populate with example tools

        # 2. Setup KnowledgeBase
        knowledge_base = SimpleKnowledgeBase() # Use SimpleKnowledgeBase

        # 3. Get LLM configuration from context for shared_llm and ActorFactory
        if not config.llm:
            raise ValueError("LLM configuration not found in context. Please ensure LLM is configured.")

        # Create a shared LLM instance for Planner and for tool selection in ActorFactory
        shared_llm_instance = create_llm_instance(config.llm)

        # 4. Initialize ActorFactory
        actor_factory = ActorFactory(
            tool_registry=tool_registry,
            knowledge_base=knowledge_base,
            default_llm_name_or_type=config.llm.model # Use the model name from config as default
        )

        # 5. Initialize Planner
        planner = Planner(llm=shared_llm_instance, goal=idea, actor_factory=actor_factory)

        # 6. Decompose initial task
        logger.info(f"Planner decomposing main goal: {idea}")
        initial_sub_tasks = asyncio.run(planner.decompose_task(idea))
        for task in initial_sub_tasks:
            planner.add_sub_task(task)

        # 7. Dynamic Execution Loop
        logger.info(f"Starting dynamic planning execution for goal: {idea}")

        processed_tasks = 0
        max_iterations = 10 # Limit iterations to prevent infinite loops during development
        while True and processed_tasks < max_iterations:
            next_task_id = None
            for task_id, task in planner.task_graph.tasks.items():
                if task.status == "pending" and not task.dependencies: # Simple check for pending tasks without dependencies
                    next_task_id = task_id
                    break

            if not next_task_id:
                # Check if all tasks are completed
                if all(t.status == "completed" for t in planner.task_graph.tasks.values()):
                    logger.info("All sub-tasks completed.")
                    break
                else:
                    logger.info("No pending tasks to process or tasks are blocked. Planner might need to re-plan.")
                    # In a more advanced system, the Planner would re-plan here.
                    break # For now, break if no immediate pending task

            sub_task_to_delegate = planner.task_graph.tasks[next_task_id]
            logger.info(f"Delegating sub-task: {sub_task_to_delegate.task_id} - {sub_task_to_delegate.objective}")
            actor = asyncio.run(planner.delegate_task(sub_task_to_delegate.task_id))

            if actor:
                logger.info(f"Actor {actor.name} ({actor.actor_id}) starting task.")
                result_message = asyncio.run(actor.run())

                # Format feedback for Planner (e.g., "TASK_ID:STATUS:DETAILS")
                # The Actor.run() returns a Message object. Assume its content is the result.
                feedback_content = f"{sub_task_to_delegate.task_id}:completed:{result_message.content}"
                feedback_message = Message(content=feedback_content, role="system", sent_from=actor.name)

                asyncio.run(planner.adjust_task_graph(feedback_message))
                processed_tasks += 1
            else:
                logger.warning(f"Could not delegate task {sub_task_to_delegate.task_id}")
                break # Exit if delegation fails unexpectedly

        logger.info("Dynamic planning execution finished.")
        return "Dynamic agent workflow executed." # Return a placeholder for now
        # --- NEW DYNAMIC AGENT WORKFLOW --- END
    else:
        stg_path = Path(recover_path)
        if not stg_path.exists() or not str(stg_path).endswith("team"):
            raise FileNotFoundError(f"{recover_path} not exists or not endswith `team`")

        from metagpt.roles import (
            Architect,
            DataAnalyst,
            Engineer2,
            ProductManager,
            TeamLeader,
        )
        from metagpt.team import Team
        company = Team.deserialize(stg_path=stg_path, context=ctx)
        idea = company.idea

        company.invest(investment)
        asyncio.run(company.run(n_round=n_round, idea=idea))
        return ctx.kwargs.get("project_path")


@app.command("", help="Start a new project.")
def startup(
    idea: str = typer.Argument(None, help="Your innovative idea, such as 'Create a 2048 game.'"),
    investment: float = typer.Option(default=3.0, help="Dollar amount to invest in the AI company."),
    n_round: int = typer.Option(default=5, help="Number of rounds for the simulation."),
    code_review: bool = typer.Option(default=True, help="Whether to use code review."),
    run_tests: bool = typer.Option(default=False, help="Whether to enable QA for adding & running tests."),
    implement: bool = typer.Option(default=True, help="Enable or disable code implementation."),
    project_name: str = typer.Option(default="", help="Unique project name, such as 'game_2048'."),
    inc: bool = typer.Option(default=False, help="Incremental mode. Use it to coop with existing repo."),
    project_path: str = typer.Option(
        default="",
        help="Specify the directory path of the old version project to fulfill the incremental requirements.",
    ),
    reqa_file: str = typer.Option(
        default="", help="Specify the source file name for rewriting the quality assurance code."
    ),
    max_auto_summarize_code: int = typer.Option(
        default=0,
        help="The maximum number of times the 'SummarizeCode' action is automatically invoked, with -1 indicating "
        "unlimited. This parameter is used for debugging the workflow.",
    ),
    recover_path: str = typer.Option(default=None, help="recover the project from existing serialized storage"),
    init_config: bool = typer.Option(default=False, help="Initialize the configuration file for MetaGPT."),
):
    """Run a startup. Be a boss."""
    if init_config:
        copy_config_to()
        return

    if idea is None:
        typer.echo("Missing argument 'IDEA'. Run 'metagpt --help' for more information.")
        raise typer.Exit()

    return generate_repo(
        idea,
        investment,
        n_round,
        code_review,
        run_tests,
        implement,
        project_name,
        inc,
        project_path,
        reqa_file,
        max_auto_summarize_code,
        recover_path,
    )


DEFAULT_CONFIG = """# Full Example: https://github.com/geekan/MetaGPT/blob/main/config/config2.example.yaml
# Reflected Code: https://github.com/geekan/MetaGPT/blob/main/metagpt/config2.py
# Config Docs: https://docs.deepwisdom.ai/main/en/guide/get_started/configuration.html
llm:
  api_type: "openai"  # or azure / ollama / groq etc.
  model: "gpt-4-turbo"  # or gpt-3.5-turbo
  base_url: "https://api.openai.com/v1"  # or forward url / other llm url
  api_key: "YOUR_API_KEY"
"""


def copy_config_to():
    """Initialize the configuration file for MetaGPT."""
    target_path = CONFIG_ROOT / "config2.yaml"

    # 创建目标目录（如果不存在）
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果目标文件已经存在，则重命名为 .bak
    if target_path.exists():
        backup_path = target_path.with_suffix(".bak")
        target_path.rename(backup_path)
        print(f"Existing configuration file backed up at {backup_path}")

    # 复制文件
    target_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    print(f"Configuration file initialized at {target_path}")


if __name__ == "__main__":
    app()