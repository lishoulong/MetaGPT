## Why

MetaGPT's current static agent roles and fixed capabilities lead to rigid responses when encountering tasks outside their pre-defined domains. This change aims to introduce dynamic adaptability to MetaGPT, allowing it to handle a broader range of complex problems by evolving its structure and capabilities. The current need is to address the inflexibility of planning and the static nature of roles, as highlighted in the provided documentation, to enable more dynamic and robust problem-solving.

## What Changes

This proposal outlines a fundamental architectural transformation within MetaGPT to support dynamic evolution of agent behaviors and roles. Key changes include:

*   **Adaptive Planner**: Implement a dynamic Planner capable of flexible task decomposition and adaptive adjustment of tasks based on real-time feedback and progress.
*   **Dynamic Actor Assembly via ActorFactory**: Introduce an ActorFactory responsible for dynamically assembling and managing Actors. This factory will focus on equipping Actors with contextually relevant internal tools, external tools, and integrated knowledge.
*   **Dynamic Actor Execution**: Each dynamically assembled Actor will be capable of creating its own execution plan and performing sub-tasks using a ReAct (Reasoning and Acting) approach.
*   **Two-Layer Progress Tracking**: Establish a robust mechanism for both the Planner and individual Actors to track their progress, ensuring the overall task execution remains on course and mitigates "getting lost" issues.
*   **Result Feedback Loop**: Actors will return execution results to the Planner, enabling iterative refinement and adaptive planning.

## Capabilities

### New Capabilities
- `dynamic-planner`: Enables the Planner to dynamically adjust and decompose tasks, overcoming planning rigidity.
- `actor-factory`: Provides mechanisms for dynamic assembly of Actors, focusing on matching internal/external tools and integrated knowledge.
- `dynamic-actor-execution`: Allows dynamically created Actors to form plans, execute sub-tasks using a ReAct approach, and manage their local progress.
- `two-layer-progress-tracking`: Introduces a system for the Planner and Actors to independently and collaboratively track task progress, preventing stagnation and ensuring task completion.

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
- `role-management`: The current static role management will be replaced or heavily modified by the dynamic ActorFactory.
- `action-execution`: The existing action execution mechanism will be augmented by dynamic Actor planning and ReAct execution.
- `message-brokering`: The current message passing between static roles will need to adapt to dynamic Actor creation and communication with the Planner.

## Impact

*   **Core Agent Orchestration**: Significant refactoring of how agents are initialized, assigned tasks, and communicate within the MetaGPT framework.
*   **Role Definition and Management**: Transition from largely static, predefined roles to dynamic, task-oriented Actor assembly.
*   **Tool Integration**: Enhanced system for dynamic discovery, selection, and integration of internal and external tools by Actors.
*   **Task Execution Flow**: Introduction of a more adaptive, iterative planning and execution cycle for complex tasks.
*   **Scalability and Flexibility**: Greatly improved ability to address a wider array of problem domains beyond software development, by allowing on-the-fly agent specialization.
*   **Observability**: New mechanisms for tracking progress at both the high-level planning and individual sub-task execution stages.
