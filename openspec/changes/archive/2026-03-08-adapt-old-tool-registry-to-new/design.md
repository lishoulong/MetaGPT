## Context

The existing MetaGPT framework has two distinct `ToolRegistry` implementations: an older one in `metagpt/tools/tool_registry.py` and a newer one in `metagpt/utils/tool_registry.py`. The new `Actor` and `ActorFactory` components are designed to interact solely with the newer `ToolRegistry`, which expects `ToolMetadata` objects containing a `tool_function` (a direct callable). Older tools, like the `Browser` tool, are registered with the old `ToolRegistry` using `Tool` objects that primarily define schemas and do not directly expose a callable `tool_function` in the required format. This discrepancy prevents the new dynamic `Actor` from utilizing existing tools without significant manual refactoring of each old tool.

## Goals / Non-Goals

**Goals:**
- Enable the new `Actor` and `ActorFactory` to seamlessly discover and execute tools previously registered with the old `ToolRegistry`.
- Minimize modifications to existing legacy tool code, achieving compatibility primarily through an adapter layer.
- Ensure that class-based tools (e.g., `Browser`) registered via the old mechanism are exposed as individual methods (e.g., `browser_type_text`, `browser_scroll_page`) to the new `ToolRegistry`.
- Maintain the `tool_function: Callable` requirement for `ToolMetadata` objects in the new registry.

**Non-Goals:**
- Refactor or rewrite the underlying implementation of existing legacy tools.
- Remove or deprecate the old `metagpt/tools/tool_registry.py` or `metagpt/tools/tool_data_type.py`. The focus is on bridging, not replacing.
- Handle complex tool lifecycle management beyond basic instantiation and method invocation within the adapter.

## Decisions

### 1. Adapter Location and Integration
- **Decision**: The adapter logic will be implemented within `metagpt/utils/tool_registry.py`, specifically within or called by the `load_and_register_all_tools` function.
- **Rationale**: This centralizes the tool discovery and registration process for the new `ToolRegistry`. By integrating it here, all tools (both new-style Python tools, LLM-prompt tools, and adapted old-style tools) are exposed through a single interface to the `ActorFactory`.
- **Alternatives Considered**:
    - **Separate module**: Could create `metagpt/utils/old_tool_adapter.py`. Rejected because `tool_registry.py` already handles tool loading and registration, making it a natural place for adapter integration.
    - **Modify old registry**: Directly modify `metagpt/tools/tool_registry.py` to also register with the new system. Rejected as it violates the goal of minimizing changes to legacy code and introduces bidirectional dependencies.

### 2. Adapting Class-Based Tools to `ToolMetadata`
- **Decision**: For class-based tools registered in the old `TOOL_REGISTRY` (e.g., `Browser`), each `method` defined in its `schemas["methods"]` will be treated as a separate `ToolMetadata` entry.
- **`ToolMetadata.name` format**: `f"{tool_name.lower()}_{method_name}"` (e.g., `browser_type_text`, `browser_scroll_page`).
- **`ToolMetadata.tool_function` implementation**: A factory function or closure will be created for each method. This callable will:
    1. Instantiates the old tool class (e.g., `Browser`) if not already done. Caching the instance will be crucial to avoid repeated instantiations.
    2. Dynamically retrieve the specific method (e.g., `browser_instance.type_text`).
    3. Return a `Callable` that takes arguments (as dictated by `ToolMetadata.input_schema`) and invokes the actual tool method.
- **Rationale**: This approach exposes the granularity of actions that an LLM can choose from, aligning with the `ToolMetadata` structure. It directly addresses the problem of `Actor` needing to call a specific function.
- **Alternatives Considered**:
    - **Register the class directly**: Registering `Browser` as a single `ToolMetadata` and expecting the LLM to understand `Browser.type_text(...)`. Rejected because `ToolMetadata` expects a direct callable, and `Actor`'s `tool_function(**args)` call expects a direct function, not a method of an instance it then needs to resolve.

### 3. Instance Management for Class-Based Tools
- **Decision**: A simple singleton-like or cached instance management will be implemented within the adapter for class-based tools. When `load_and_register_all_tools` processes an old-style class tool, it will create *one* instance of that class (e.g., `Browser`). This instance will then be reused across all `tool_function` wrappers created for its methods.
- **Rationale**: Avoids redundant object creation, which could be resource-intensive (e.g., launching multiple browser instances). Simplifies the `tool_function` wrapper by allowing it to capture a pre-existing instance.
- **Alternatives Considered**:
    - **Instance per invocation**: Create a new instance every time a tool method is called. Rejected due to performance overhead and potential state issues (e.g., `Browser` maintaining session state).
    - **Instance passed via arguments**: Require the `Actor` to explicitly manage and pass tool instances. Rejected as it adds complexity to the `Actor`'s prompt and execution logic, deviating from the simple `tool_function(**args)` model.

### 4. Parameter Mapping
- **Decision**: The `input_schema` from the old `Tool`'s `schemas["parameters"]` or `schemas["methods"][method_name]["parameters"]` will be directly used for the new `ToolMetadata.input_schema`. The `tool_function` wrapper will ensure that `**kwargs` from the `Actor` are passed correctly to the underlying tool method. Type hints from the old tool's methods will be used to enrich the `input_schema` where possible, similar to `extract_tool_metadata_from_function`.
- **Rationale**: Reuses existing schema definitions, reducing duplication and ensuring consistency.

### 5. Asynchronous Handling
- **Decision**: The `tool_function` wrappers for methods of old tools will be `async def` functions, even if the underlying method is synchronous. If the underlying method is synchronous, `await` will not be used inside the wrapper; if it is `async`, `await` will be used. This ensures all `tool_function`s are awaitable, compatible with `Actor`'s `await tool_meta.tool_function(**args)`.
- **Rationale**: Simplifies the `Actor`'s execution loop by ensuring all tool calls are treated uniformly as awaitable.

## Risks / Trade-offs

- **Instance Lifecycle Management**:
    - **Risk**: If class-based tools have complex setup/teardown (e.g., `Browser.start()`/`Browser.stop()`), the current simple singleton instance management might not be sufficient. Improper lifecycle management could lead to resource leaks or unexpected behavior.
    - **Mitigation**: Start with simple instantiation. If issues arise, extend the adapter to include `start`/`stop` methods or integrate with a broader tool lifecycle manager if MetaGPT develops one.
- **Parameter Serialization/Deserialization**:
    - **Risk**: Discrepancies between how the old tools expect parameters (e.g., specific types, complex objects) and how the LLM generates/the adapter passes them might lead to runtime errors. The `Actor`'s current argument parsing logic (`json.loads(value)`) might not cover all edge cases.
    - **Mitigation**: Thorough testing with various old tools and their methods. Enhance the `ToolMetadata.input_schema` with more precise type information and consider more robust argument parsing in the `Actor` or adapter if needed.
- **Docstring/Schema Extraction Accuracy**:
    - **Risk**: The quality of `ToolMetadata.description` and `input_schema` for adapted tools depends heavily on the accuracy and completeness of the old tool's docstrings and schema definitions.
    - **Mitigation**: Leverage `metagpt.tools.tool_convert.convert_code_to_tool_schema` as much as possible for schema generation. Provide clear guidelines for future tool development to ensure rich metadata.
- **Performance Overhead**:
    - **Risk**: Dynamic instantiation and wrapping of methods could introduce a slight performance overhead compared to direct calls.
    - **Mitigation**: Monitor performance. The overhead is expected to be minimal, especially since instantiation will be cached. The benefits of unification outweigh this minor cost.

## Open Questions

- Should the adapter specifically target `metagpt.tools.libs.browser` first as a proof of concept, or aim for a generic solution for all class-based tools? (Initial plan is generic, using `Browser` as the primary test case).
- Are there any stateful considerations for old tools beyond simple instance caching that need to be addressed (e.g., concurrent access to a single tool instance)? (Assume current tools are mostly designed for single-user interaction, but keep in mind for future scaling).
