## Context

The current MetaGPT framework excels in structured software development tasks by leveraging a team of static, pre-defined agent roles with fixed capabilities. However, this design inherently limits its adaptability and problem-solving scope when encountering novel or out-of-domain tasks that do not align with the established roles and their associated toolsets. The existing system can exhibit "planning rigidity" and "role solidification," leading to inefficient or unresolvable outcomes for problems requiring dynamic adaptation or specialized, on-the-fly expertise. This design aims to address these limitations by introducing dynamic planning, actor assembly, and execution capabilities, as outlined in the initial proposal.

## Goals / Non-Goals

**Goals:**
*   Enable a `Planner` to perform adaptive and dynamic task decomposition, allowing for flexible adjustment of sub-tasks based on execution feedback and evolving context.
*   Implement an `ActorFactory` capable of dynamically assembling `Actors` (dynamic experts) tailored to specific sub-tasks, ensuring they are equipped with the most relevant internal tools, external tools, and built-in knowledge.
*   Design `Actors` to create their own execution plans and perform sub-tasks using a ReAct (Reasoning and Acting) approach, enhancing their autonomy and problem-solving ability.
*   Establish a two-layer progress tracking mechanism, where both the `Planner` and individual `Actors` can monitor their respective progress, preventing task stagnation and improving overall task oversight.
*   Create a robust feedback loop allowing `Actors` to return execution results, observations, and blockages to the `Planner` for iterative refinement and adaptive strategic adjustments.

**Non-Goals:**
*   Completely overhaul or replace the fundamental multi-agent communication and environment components of MetaGPT, but rather extend and integrate with them.
*   Develop a comprehensive suite of new domain-specific tools from scratch; the focus is on enabling dynamic integration and utilization of *existing* internal and external tools.
*   Achieve perfect human-level intuition or creativity in dynamic task decomposition and actor assembly in the initial iteration, but to provide a significant improvement over static role limitations.
*   Address all potential performance optimizations in this design phase; initial focus is on functional correctness and architectural soundness.

## Decisions

### 1. Adaptive Planner Design
*   **Approach**: The `Planner` will leverage a Large Language Model (LLM) as its primary reasoning engine. It will be responsible for interpreting the high-level goal, recursively decomposing it into a hierarchy of sub-tasks, and maintaining the overall task graph. Its planning will be iterative, adjusting the task breakdown based on feedback from `Actors` (e.g., sub-task completion, failure, new observations, unexpected complexities).
*   **Prompt Engineering**: The Planner's LLM will be guided by sophisticated prompt engineering, which includes the main goal, current progress, available capabilities (via the ActorFactory's registry), and historical context. This prompt will enable the LLM to generate adaptive sub-task definitions and determine which Actor capabilities are required.
*   **Knowledge/Heuristics**: The Planner will have access to a knowledge base (potentially a small, domain-agnostic RAG system or a set of heuristic rules) to guide task decomposition, especially for common patterns or known problem types.
*   **Task Representation**: Sub-tasks will be formally represented (e.g., as structured JSON objects) including their objective, required inputs, expected outputs, and estimated dependencies.

### 2. ActorFactory Architecture
*   **Function**: The `ActorFactory` will serve as the central component for dynamic `Actor` creation and configuration. It acts as a broker between the `Planner`'s sub-task requirements and the available `Actor` resources.
*   **Capability Matching**: Upon receiving a sub-task from the `Planner`, the `ActorFactory` will analyze the sub-task's requirements (e.g., keywords, implied tools, necessary domain knowledge) and match them against a registry of available tools and knowledge modules.
*   **Actor Assembly**: For each sub-task, the `ActorFactory` will dynamically instantiate an `Actor` instance. This involves:
    1.  **LLM Configuration**: Assigning an appropriate LLM (potentially different models for different complexities/costs) to the `Actor`.
    2.  **Tool Provisioning**: Injecting the matched internal and external tools (from a `ToolRegistry`) into the `Actor`'s executable environment.
    3.  **Knowledge Contextualization**: Loading relevant, domain-specific knowledge (e.g., through RAG from a knowledge base, or specific pre-trained embeddings) into the `Actor`'s working memory or prompt context.
*   **ToolRegistry**: A centralized, discoverable `ToolRegistry` will manage metadata for all available tools. This metadata will include tool descriptions, usage instructions, input/output schemas, and any associated costs or access requirements. This allows the `ActorFactory` to programmatically select the best tool(s) for a given sub-task.
*   **Knowledge Management**: A modular knowledge management system will allow `Actors` to access and integrate external domain knowledge efficiently. This could involve vector databases for semantic search or structured knowledge graphs.

### 3. Actor Execution (ReAct Approach)
*   **ReAct Loop**: Each dynamically assembled `Actor` will operate on a modified ReAct (Reasoning and Acting) loop:
    1.  **Observe**: Receive the specific sub-task, its context, and any initial inputs from the `Planner`.
    2.  **Think (Reason)**: The `Actor`'s LLM analyzes the observation, consults its integrated knowledge, and utilizes its assigned tools to formulate a step-by-step execution plan (sequence of thoughts and actions).
    3.  **Act**: The `Actor` executes one or more steps of its plan by invoking its provisioned tools. Tools will have defined input and output.
    4.  **Observe**: The `Actor` processes the output from the executed tool(s), updating its internal state and potentially revising its plan.
    5.  **Report**: Periodically or upon significant events (completion, blockage, new insights), the `Actor` will report its status and results back to the `Planner`.
*   **Internal State**: Each `Actor` will maintain its own internal working memory for its sub-task, including intermediate results, observed states, and partial plans.

### 4. Two-Layer Progress Tracking
*   **Planner-Level Tracking**: The `Planner` will maintain a global view of the task graph, tracking the status (`pending`, `in_progress`, `completed`, `failed`, `blocked`) of each sub-task. It aggregates progress reports from `Actors`.
*   **Actor-Level Tracking**: Each `Actor` will track its granular progress on its assigned sub-task, including which steps of its ReAct plan have been executed, which tools were used, and any intermediate outputs. This detailed local state is periodically summarized and reported to the `Planner`.
*   **Visibility**: Both internal system logging and potential external monitoring dashboards will be designed to visualize this two-layer progress, allowing for better debugging and human oversight.

### 5. Result Feedback Loop
*   **Actor-to-Planner**: `Actors` will proactively send structured messages to the `Planner` indicating:
    *   `SubTask_Completed`: With final results.
    *   `SubTask_Failed`: With error details and context.
    *   `SubTask_Blocked`: With reasons for blockage and potential requirements for unblocking.
    *   `New_Observation`: Significant new information discovered during execution that might impact the overall plan.
    *   `Partial_Progress`: Periodic updates on long-running tasks.
*   **Planner Response**: The `Planner` will consume these feedback messages and use them to:
    *   Update the task graph.
    *   Initiate re-planning for failed or blocked sub-tasks.
    *   Modify subsequent sub-tasks based on new observations.
    *   Trigger new Actor assemblies via the `ActorFactory`.

## Risks / Trade-offs

*   **Increased System Complexity**: The introduction of dynamic planning, actor assembly, and ReAct execution significantly increases the architectural complexity of MetaGPT. This requires careful design of interfaces, robust error handling, and comprehensive testing strategies.
    *   **Mitigation**: Adopt a modular design with clear separation of concerns for the `Planner`, `ActorFactory`, `Actor` core, and `ToolRegistry`. Implement strong type checking and API contracts.
*   **Performance Overhead and Latency**: Dynamic LLM calls for planning and reasoning, along with runtime Actor assembly and tool invocation, can introduce noticeable latency and increase computational costs compared to static execution.
    *   **Mitigation**: Implement intelligent caching for `Actor` configurations and tool outputs. Explore smaller, specialized LLMs for specific reasoning steps within `Actors`. Optimize tool invocation mechanisms. Consider asynchronous processing where appropriate.
*   **LLM Reliability and Hallucination**: Heavy reliance on LLMs for critical planning and reasoning steps introduces risks of incorrect task decomposition, suboptimal plans, or factual inaccuracies (hallucinations).
    *   **Mitigation**: Implement rigorous prompt engineering and few-shot examples for LLM calls. Incorporate validation steps for LLM-generated plans/outputs. Design self-correction mechanisms where `Actors` can identify and report inconsistencies. Human-in-the-loop for high-stakes planning or critical decisions.
*   **Tool Integration and Management Challenges**: Managing a dynamic `ToolRegistry` with diverse internal and external tools (each with its own API, dependencies, and potential failure modes) presents significant integration and maintenance challenges.
    *   **Mitigation**: Enforce a standardized tool interface/wrapper. Implement robust error handling and retry mechanisms for tool calls. Develop monitoring and health-checking for integrated tools. Clearly define tool capabilities and limitations.
*   **State Management and Consistency**: Maintaining consistent state across a dynamic `Planner` and multiple concurrently executing `Actors`, especially during re-planning or error recovery, can be difficult.
    *   **Mitigation**: Design explicit state representations for tasks and actors. Utilize persistent memory mechanisms for Actor context. Implement clear communication protocols and synchronization points between `Planner` and `Actors`.
*   **Debugging and Observability**: Debugging issues in a highly dynamic and distributed agent system can be complex. Understanding why an `Actor` chose a certain path or why the `Planner` re-planned requires robust logging and visualization.
    *   **Mitigation**: Implement comprehensive, structured logging at all layers (Planner, ActorFactory, Actors). Develop visualization tools to trace task decomposition, Actor assignments, ReAct steps, and feedback loops.

## Open Questions

*   **Granularity of Actor Specialization**: How granular should `Actors` be? Should they be specialized per sub-task type, or more general-purpose but dynamically configured?
*   **Tool Access Control/Security**: How will access to sensitive external tools or data be managed in a dynamic `ActorFactory` environment?
*   **Learning and Adaptation**: Beyond explicit feedback, how can the system learn from past successes and failures to improve its planning and actor assembly strategies over time?
*   **Human-in-the-Loop Integration**: Where are the optimal intervention points for human operators to guide, correct, or refine the dynamic process?
