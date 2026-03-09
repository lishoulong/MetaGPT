## Context

The current MetaGPT framework utilizes a `ToolRegistry` to manage tools and an `ActorFactory` to dynamically assemble actors. However, the existing mechanism for tool provision lacks the ability to dynamically discover, load, and integrate diverse types of tools. Specifically, there is no standardized way to incorporate pre-defined Python utilities (like filesystem or Git operations), new Python-based skills, or LLM-prompt-based tools (defined by `config.json` and prompt files) as dynamically discoverable and usable tools for actors. This limits the extensibility, reusability of specialized functionalities, and the ability of actors to leverage existing framework capabilities.

## Goals / Non-Goals

**Goals:**
- Implement a comprehensive tool discovery mechanism that can find Python callable tools (including core MetaGPT utilities and new Python skills) and LLM-prompt-based tools from configurable directories.
- Provide robust methods to extract metadata from these diverse tool types for `ToolRegistry` registration.
- Enable dynamic registration of all discovered tool types into the `ToolRegistry`.
- Implement a callable wrapper for LLM-prompt-based tools to make them compatible with the `ToolRegistry`'s invocation mechanism.
- Modify `ActorFactory` to leverage this enhanced tool discovery and registration for provisioning actors with relevant tools, abstracting away their underlying implementation type.

**Non-Goals:**
- Redefining the `ToolMetadata` structure or the core `ToolRegistry` API beyond adding support for diverse tool types and their invocation.
- Implementing a complex tool versioning or dependency management system.
- Modifying how existing, manually registered tools function if they are outside this new dynamic discovery flow.
- Building new core utilities (e.g., a new Git client from scratch); the goal is to integrate existing ones.

## Decisions

### Decision: Tool Discovery Location
- **Choice**: Introduce a configuration parameter (e.g., `TOOL_DIRS` in `config.py` or similar) to specify directories where tools should be discovered. Default to a `tools/` and `skills/` directory within the MetaGPT project root.
- **Rationale**: Provides flexibility for users to define custom tool locations while offering sensible defaults that acknowledge both generic `tools` and specific `skills` directories.
- **Alternatives Considered**: Hardcoding specific directories (less flexible); relying solely on environment variables (less discoverable).

### Decision: Tool Type Classification and Metadata Definition
- **Choice**: Tools will be broadly classified into two main types based on discovery:
    1.  **Python Callable Tools**: Discovered from `.py` files. Metadata will primarily be extracted from `ToolMetadata` objects defined alongside the callable, or fallback to docstrings/type hints. Existing core utilities will be explicitly wrapped into `ToolMetadata` for registration.
    2.  **LLM-Prompt-Based Tools**: Discovered from subdirectories containing `config.json` (for metadata and LLM parameters) and a prompt file (e.g., `skprompt.txt`, `.txt`). Metadata will be parsed directly from `config.json`.
- **Rationale**: This classification directly addresses the identified existing tool formats. `ToolMetadata` remains the canonical representation within the `ToolRegistry`, but its population varies by tool type.
- **Alternatives Considered**: A single, complex metadata standard (difficult to apply to diverse existing formats); separate registries for each tool type (increases complexity of `ActorFactory` provisioning).

### Decision: Tool Loading, Wrapping, and Registration Process
- **Choice**: A new utility module (e.g., `metagpt.utils.tool_loader.py`) will be responsible for:
    - Iterating through configured `TOOL_DIRS`.
    - Identifying Python callable tools and LLM-prompt-based tool definition directories.
    - For Python callable tools: Importing modules, extracting metadata, and packaging the callable function into a `ToolMetadata` object.
    - For LLM-prompt-based tools: Reading `config.json` for metadata and LLM parameters, reading the prompt file, and creating a **callable wrapper function**. This wrapper will take tool arguments, format the prompt, call the LLM (`BaseLLM.aask`), and return the result. This wrapper function will then be packaged into a `ToolMetadata` object.
    - Finally, using `ToolRegistry.register_tool()` to add all generated `ToolMetadata` objects.
- **Rationale**: Centralizes tool management logic. The callable wrapper for LLM-prompt-based tools ensures that the `ToolRegistry` (and by extension, the `Actor`) interacts with all tools uniformly, regardless of their internal implementation (Python function vs. LLM call).
- **Alternatives Considered**: `ToolRegistry` directly handling prompt formatting/LLM calls (violates single responsibility); lazy loading tools (adds complexity, less predictable startup).

### Decision: `ActorFactory` Integration
- **Choice**: `ActorFactory`'s `create_actor_for_task` method will be updated. After receiving the sub-task objective, it will query its LLM (as it currently does for tool recommendations) to identify relevant tools (now registered as `ToolMetadata` objects in the `ToolRegistry`). It will then retrieve these tools and pass them to the `Actor` instance. The `Actor`'s ReAct loop will simply invoke the `tool_function` within the `ToolMetadata` object, unaware if it's a direct Python call or an LLM wrapper.
- **Rationale**: Leverages existing LLM capabilities for tool selection. The abstraction provided by the callable wrapper keeps the `Actor`'s logic clean and consistent across diverse tool types.

### Decision: Handling Duplicate Tool Names
- **Choice**: If a discovered tool's name conflicts with an already registered tool, the `ToolRegistry.register_tool` method will log a warning and skip the registration of the new tool.
- **Rationale**: Prevents accidental overwrites and ensures predictable tool behavior. Users can explicitly manage naming to avoid conflicts.

## Risks / Trade-offs

- **Performance Overhead**: Iterating through many tool directories and files at startup, and dynamic loading of modules, could introduce a noticeable delay.
    - **Mitigation**: Optimize discovery process (e.g., intelligent caching, parallel loading), ensure tool modules are lightweight, and consider options for deferred loading of less critical tools.
- **LLM Prompt Context Bloat (for LLM-prompt-based tools)**: If tool descriptions or prompts are very long, using them in `ActorFactory`'s LLM prompt for tool selection could consume significant tokens.
    - **Mitigation**: Ensure `ToolMetadata` descriptions are concise. `ActorFactory` could selectively provide tool descriptions to the LLM (e.g., only names and brief descriptions initially, full details on selection).
- **Security Implications**: Loading arbitrary Python files and executing prompts from configurable directories introduces security risks if not carefully managed (e.g., malicious code in Python tools, prompt injection vulnerabilities in LLM-prompt-based tools).
    - **Mitigation**: Clearly document security implications. Advise users to use trusted tool sources. Implement sanity checks for Python tool files (e.g., linting, basic static analysis) and for `config.json`/prompt files (e.g., schema validation, input sanitization). Consider sandboxing for advanced scenarios (future work).
- **Tool Interface Evolution**: Future changes to how tools are defined or how `ToolMetadata` works could break existing tools.
    - **Mitigation**: Maintain clear documentation on tool development guidelines and provide migration paths for breaking changes. Establish a versioning strategy for `config.json` schema.

## Open Questions

- What is the precise schema for `config.json` and the structure of prompt files to ensure consistent parsing and wrapping for LLM-prompt-based tools?
- Should there be a mechanism to validate the input schema of tools beyond basic type hints, especially for LLM-prompt-based tools?
- How should existing core MetaGPT utilities be identified and exposed in a `ToolMetadata`-compatible way? Will they be auto-discovered or require explicit registration?
- How will conflicts between tool names from different discovery sources (e.g., a Python callable tool and an LLM-prompt-based tool having the same name) be prioritized or resolved beyond simple logging?
