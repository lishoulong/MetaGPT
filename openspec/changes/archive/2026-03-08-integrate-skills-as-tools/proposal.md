## Why

The current actor assembly mechanism lacks a direct way to integrate pre-defined "skills" and core MetaGPT utilities as dynamically discoverable and usable tools for actors. This limits the extensibility, reusability of specialized functionalities, and the ability of actors to leverage existing framework capabilities within the MetaGPT framework.

## What Changes

- Introduce a comprehensive mechanism to discover and register various types of tools into the `ToolRegistry`, including:
    - **Existing Python Utilities**: Core MetaGPT functionalities like filesystem operations, Git operations, and terminal execution, formalized as callable tools.
    - **Python Callable Skills**: Functions or classes from designated skill directories with embedded metadata.
    - **LLM-Prompt-Based Tools**: Tools defined by configuration (`config.json`) and prompt templates (`.txt` or similar) from designated skill directories.
- Extend `ActorFactory` to automatically provision actors with these registered tools based on task requirements and LLM recommendations, abstracting away the underlying implementation type of the tool.
- Ensure all types of tools conform to a defined interface/metadata structure for proper registration, validation, and invocation by actors.

## Capabilities

### New Capabilities
- `tool-discovery`: Ability to find and load both Python-based and config/prompt-based tools from configurable directories, as well as identify existing core utilities.
- `dynamic-tool-registration`: Register diverse types of discovered tools (Python callables, LLM-prompt-based, core utilities) into the `ToolRegistry` with appropriate metadata, including a mechanism to wrap LLM-prompt-based tools into a callable format.
- `actor-tool-provisioning`: `ActorFactory` to dynamically provide actors with relevant tools, abstracting tool implementation details.

### Modified Capabilities
- None

## Impact

- `metagpt/utils/tool_registry.py`: Will be extended to handle dynamic registration of various tool types and potentially an abstraction layer for tool invocation.
- `metagpt/actor/actor_factory.py`: Will be modified to incorporate comprehensive tool discovery and provisioning logic.
- New module/utility for tool discovery and wrapping of LLM-prompt-based tools (e.g., `metagpt/utils/tool_loader.py` or similar).
- Existing core utility modules (e.g., `metagpt/utils/file.py`, `metagpt/utils/git_repository.py`) might need minor modifications to expose their functions in a `ToolMetadata`-compatible way or to be wrapped by the new tool loader.
- Potential impact on actor prompt engineering to encourage broader tool usage.
