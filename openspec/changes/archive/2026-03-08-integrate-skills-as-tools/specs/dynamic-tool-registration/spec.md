## ADDED Requirements

### Requirement: Dynamic Tool Registration
The `ToolRegistry` SHALL provide a method to dynamically register discovered tools of various types.
Each registered tool SHALL be associated with its extracted metadata, including name, description, usage example, input schema, and the underlying callable function or a callable wrapper.
The registration process SHALL handle potential conflicts (e.g., duplicate tool names) by logging a warning and preventing overwrites or by providing an explicit overwrite option.

#### Scenario: Register a Python callable tool
- **WHEN** a Python callable tool (e.g., an existing utility function, a new Python skill) with unique name and valid metadata is provided to the `ToolRegistry`'s registration method
- **THEN** the tool SHALL be successfully added to the registry and be retrievable by its name

#### Scenario: Register an LLM-prompt-based tool
- **WHEN** an LLM-prompt-based tool (defined by `config.json` and a prompt file) is processed by a wrapper and provided to the `ToolRegistry`'s registration method with unique name and valid metadata
- **THEN** the tool SHALL be successfully added to the registry, its callable wrapper used for invocation, and be retrievable by its name

#### Scenario: Handle duplicate tool name
- **WHEN** an attempt is made to register a tool with a name that already exists in the `ToolRegistry`
- **THEN** the `ToolRegistry` SHALL log a warning and not overwrite the existing tool by default

### Requirement: Tool Access, Invocation, and Wrapping
Registered tools SHALL be accessible by their name from the `ToolRegistry`.
The `ToolRegistry` SHALL enable the invocation of registered tool functions or their callable wrappers with provided arguments, ensuring proper argument validation against the tool's input schema.
For LLM-prompt-based tools, a callable wrapper SHALL be created during registration that takes arguments, formats the prompt using the prompt template, sends it to an LLM, and returns the LLM's response.

#### Scenario: Retrieve a registered tool
- **WHEN** a valid tool name is used to query the `ToolRegistry`
- **THEN** the corresponding `ToolMetadata` object, including the callable function/wrapper, SHALL be returned

#### Scenario: Invoke a Python callable tool with valid arguments
- **WHEN** a registered Python callable tool is invoked via the `ToolRegistry` with arguments matching its input schema
- **THEN** the underlying Python function SHALL be called with the provided arguments and its result returned

#### Scenario: Invoke an LLM-prompt-based tool with valid arguments
- **WHEN** a registered LLM-prompt-based tool is invoked via the `ToolRegistry` with arguments matching its input schema
- **THEN** its callable wrapper SHALL format the prompt, call the LLM, and return the LLM's response

#### Scenario: Invoke a registered tool with invalid arguments
- **WHEN** a registered tool is invoked via the `ToolRegistry` with arguments that do not match its input schema
- **THEN** the `ToolRegistry` SHALL raise an error or return a clear error message indicating argument mismatch
