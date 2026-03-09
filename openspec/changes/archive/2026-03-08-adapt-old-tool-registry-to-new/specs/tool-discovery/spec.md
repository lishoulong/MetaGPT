## ADDED Requirements

### Requirement: Enhanced Tool Discovery Process
The system SHALL discover Python callable tools, LLM-prompt-based tools, and adapt legacy tools registered through `metagpt/tools/tool_registry.py`, integrating all into the unified `ToolRegistry`.

#### Scenario: Legacy tools included in discovery
- **WHEN** `load_and_register_all_tools` is executed
- **THEN** it SHALL query `metagpt/tools/tool_registry.py` for registered `Tool` objects.
- **THEN** it SHALL use the adapter to convert these `Tool` objects into `ToolMetadata` and register them in the unified `ToolRegistry`.
