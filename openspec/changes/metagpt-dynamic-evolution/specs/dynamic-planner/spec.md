## ADDED Requirements

### Requirement: Dynamic Planner Task Decomposition
The system SHALL enable the Planner to dynamically decompose high-level tasks into sub-tasks based on the current context and available Actor capabilities.

#### Scenario: Initial task decomposition
- **WHEN** the Planner receives a new high-level task
- **THEN** the Planner SHALL use an LLM to decompose it into an initial set of sub-tasks
- **AND THEN** each sub-task SHALL be represented with its objective, required inputs, and expected outputs.

#### Scenario: Adaptive task adjustment
- **WHEN** the Planner receives feedback from an Actor indicating a sub-task failure or new observation
- **THEN** the Planner SHALL re-evaluate the overall task graph and dynamically adjust or re-decompose affected sub-tasks.

### Requirement: Planner Contextual Awareness
The Planner SHALL maintain awareness of the overall project goal, current progress, and the status of all active sub-tasks and Actors.

#### Scenario: Accessing current state
- **WHEN** the Planner needs to make a decomposition or reassignment decision
- **THEN** the Planner SHALL access the aggregated status of all sub-tasks and Actor reports to inform its decision.
