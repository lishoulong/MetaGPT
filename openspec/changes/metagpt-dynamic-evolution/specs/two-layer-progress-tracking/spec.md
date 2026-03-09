## ADDED Requirements

### Requirement: Planner-Level Task Tracking
The `Planner` SHALL maintain a global view of the overall task graph, including the status of all sub-tasks and the `Actors` assigned to them.

#### Scenario: Planner updates sub-task status
- **WHEN** the `Planner` receives a progress report (e.g., completion, failure, blockage) from an `Actor`
- **THEN** the `Planner` SHALL update the status of the corresponding sub-task in its global task graph.

#### Scenario: Planner identifies blocked sub-tasks
- **WHEN** the `Planner` detects a sub-task is blocked based on `Actor` feedback or lack of progress
- **THEN** the `Planner` SHALL log the blockage and potentially initiate re-planning or escalate the issue.

### Requirement: Actor-Level Sub-task Progress Tracking
Each `Actor` SHALL track its own granular progress on its assigned sub-task, including execution steps and tool usage.

#### Scenario: Actor tracks ReAct steps
- **WHEN** an `Actor` executes a step in its ReAct loop (Observe, Think, Act)
- **THEN** the `Actor` SHALL record the current step and any relevant intermediate outcomes in its internal memory.

#### Scenario: Actor reports progress to Planner
- **WHEN** an `Actor` reaches a significant milestone (e.g., sub-task completion, failure, blockage, new observation) or at periodic intervals
- **THEN** the `Actor` SHALL send a structured progress report to the `Planner`.
