## ADDED Requirements

### Requirement: Expanded Tool Selection
The `ActorFactory`'s LLM-based tool selection process SHALL consider all tools available in the unified `ToolRegistry`, including newly adapted legacy tools, when recommending tools for a given sub-task objective.

#### Scenario: LLM recommends adapted tool
- **WHEN** `ActorFactory` generates a tool selection prompt for an LLM
- **THEN** the prompt SHALL include descriptions of adapted legacy tools (e.g., `browser_type_text`).
- **THEN** the LLM SHALL be able to recommend an adapted legacy tool (e.g., `browser_type_text`) if it is relevant to the sub-task.
