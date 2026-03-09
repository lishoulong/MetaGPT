## ADDED Requirements

### Requirement: ActorFactory Dynamic Assembly
The `ActorFactory` SHALL dynamically assemble and configure `Actors` based on the requirements of a given sub-task from the Planner.

#### Scenario: Assemble Actor for specific sub-task
- **WHEN** the `ActorFactory` receives a sub-task with specified requirements (e.g., skill, tool usage, knowledge domain)
- **THEN** the `ActorFactory` SHALL select an appropriate LLM for the `Actor`
- **AND THEN** the `ActorFactory` SHALL provision the `Actor` with relevant internal and external tools from the `ToolRegistry`
- **AND THEN** the `ActorFactory` SHALL contextualize the `Actor` with necessary domain-specific knowledge (e.g., via RAG from a knowledge base).

### Requirement: Tool Registry Management
The `ActorFactory` SHALL utilize a centralized `ToolRegistry` to manage, discover, and select tools for Actor assembly.

#### Scenario: Tool lookup and provisioning
- **WHEN** a sub-task requires a specific capability (e.g., "access financial data")
- **THEN** the `ActorFactory` SHALL query the `ToolRegistry` to identify and retrieve the appropriate tool(s) metadata and access information
- **AND THEN** the `ActorFactory` SHALL provision these tool(s) to the dynamically created `Actor`.

### Requirement: Knowledge Contextualization
The `ActorFactory` SHALL ensure that dynamically assembled `Actors` are provided with relevant contextual knowledge for their assigned sub-tasks.

#### Scenario: Embedding knowledge into Actor context
- **WHEN** a sub-task requires specific domain knowledge
- **THEN** the `ActorFactory` SHALL load or link relevant knowledge (e.g., from a vector database or specific knowledge graphs) into the `Actor`'s working memory or prompt context.
