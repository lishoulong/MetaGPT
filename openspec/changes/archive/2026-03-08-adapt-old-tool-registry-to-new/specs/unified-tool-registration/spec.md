## ADDED Requirements

### Requirement: Unified Tool Access
The system SHALL provide a single, unified `ToolRegistry` through `metagpt/utils/tool_registry.py` that allows discovery and invocation of all available tools, irrespective of their original registration mechanism (old `metagpt/tools/tool_registry.py` or new).

#### Scenario: Actor discovers all tools
- **WHEN** an `ActorFactory` initializes and queries the unified `ToolRegistry`
- **THEN** all tools registered via the old mechanism (after adaptation) and the new mechanism are available for selection.

#### Scenario: Actor invokes adapted tool
- **WHEN** an `Actor` receives an `Action` to invoke an adapted tool (e.g., `browser_type_text`)
- **THEN** the unified `ToolRegistry` provides the corresponding `ToolMetadata` with a callable `tool_function`.
- **THEN** the `Actor` successfully executes the `tool_function` to perform the intended operation.
