## ADDED Requirements

### Requirement: Dynamic Actor Tool Provisioning
The `ActorFactory` SHALL dynamically provision actors with relevant tools from the `ToolRegistry` based on the sub-task objective and LLM recommendations.
The `ActorFactory` SHALL query the LLM to identify the most relevant tools for a given sub-task objective, regardless of whether they are Python callable or LLM-prompt-based tools.
The `ActorFactory` SHALL then retrieve these tools from the `ToolRegistry` and inject them into the `Actor` instance being created, abstracting their underlying implementation type.

#### Scenario: Provision actor with recommended Python callable tools
- **WHEN** `ActorFactory` is asked to create an actor for a sub-task, and the LLM recommends Python callable tools
- **THEN** the `ActorFactory` SHALL provision the created actor with the recommended Python callable tools from the `ToolRegistry`

#### Scenario: Provision actor with recommended LLM-prompt-based tools
- **WHEN** `ActorFactory` is asked to create an actor for a sub-task, and the LLM recommends LLM-prompt-based tools
- **THEN** the `ActorFactory` SHALL provision the created actor with the recommended LLM-prompt-based tools (via their callable wrappers) from the `ToolRegistry`

#### Scenario: Provision actor without recommended tools
- **WHEN** `ActorFactory` is asked to create an actor for a sub-task for which no tools are recommended by the LLM
- **THEN** the created actor SHALL be provisioned with an empty set of tools

### Requirement: Contextual Knowledge Injection
The `ActorFactory` SHALL inject relevant contextual knowledge into the `Actor` instance being created, based on the sub-task objective and available knowledge base.

#### Scenario: Inject relevant knowledge
- **WHEN** `ActorFactory` creates an actor for a sub-task
- **THEN** the `ActorFactory` SHALL query the `KnowledgeBase` for information relevant to the sub-task objective and provide it to the actor
