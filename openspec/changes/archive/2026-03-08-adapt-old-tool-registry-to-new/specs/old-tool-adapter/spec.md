## ADDED Requirements

### Requirement: Old Tool Adaptation
The `metagpt/utils/tool_registry.py` SHALL include an adapter mechanism that automatically converts `Tool` objects registered in the old `metagpt/tools/tool_registry.py` into `ToolMetadata` objects compatible with the new system.

#### Scenario: Class-based tool methods adapted
- **WHEN** an old `Tool` object representing a class (e.g., `Browser`) is processed by the adapter
- **THEN** a separate `ToolMetadata` object SHALL be created for each public method specified in the old `Tool`'s schemas (e.g., `browser_type_text`, `browser_scroll_page`).
- **THEN** each generated `ToolMetadata` object SHALL have a `name` in the format `"{tool_name.lower()}_{method_name}"`.
- **THEN** each `ToolMetadata` object SHALL contain a `tool_function` that, when called, correctly instantiates (if necessary, only once per tool class) and invokes the corresponding method of the old tool.

#### Scenario: Parameter mapping
- **WHEN** an adapted tool's `tool_function` is invoked with `**kwargs`
- **THEN** the adapter SHALL correctly map these arguments to the parameters expected by the original old tool method.

#### Scenario: Asynchronous compatibility
- **WHEN** an adapted tool's `tool_function` is invoked by an `Actor`
- **THEN** the `tool_function` SHALL be awaitable, regardless of whether the original method is synchronous or asynchronous.
