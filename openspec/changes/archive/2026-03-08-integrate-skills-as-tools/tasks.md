## 1. Tool Discovery Mechanism

- [x] 1.1 Create `metagpt/utils/tool_loader.py` module.
- [x] 1.2 Implement a function in `tool_loader.py` to discover Python files (for callable tools) in configurable directories.
- [x] 1.3 Implement a function in `tool_loader.py` to discover subdirectories containing `config.json` and prompt files (for LLM-prompt-based tools) in configurable directories.
- [x] 1.4 Implement logic to identify callable functions within discovered Python files and extract `ToolMetadata` from objects, docstrings, or type hints.
- [x] 1.5 Implement logic to parse `config.json` and prompt files for LLM-prompt-based tools and construct their `ToolMetadata`.
- [x] 1.6 Add configuration option (e.g., in `metagpt/config.py` or similar) for `TOOL_DIRS` to specify tool search paths.
- [x] 1.7 Identify existing core MetaGPT utilities (e.g., `metagpt/utils/file.py`, `metagpt/utils/git_repository.py` functions) and ensure they can be wrapped/registered as Python callable tools.

## 2. Dynamic Tool Registration and Wrapping

- [x] 2.1 Modify `metagpt/utils/tool_registry.py` to add a method for registering tools (callable and metadata), ensuring it can handle `ToolMetadata` objects containing either direct Python callables or callable wrappers.
- [x] 2.2 Implement logic in `ToolRegistry` to handle duplicate tool names gracefully (log warning, prevent overwrite).
- [x] 2.3 Implement a callable wrapper function within `tool_loader.py` (or a helper) for LLM-prompt-based tools, which formats the prompt and calls the LLM (`BaseLLM.aask`).
- [x] 2.4 Integrate `tool_loader.py` with `ToolRegistry` initialization to automatically load and register all discovered tools (Python callable and LLM-prompt-based) at system startup.

## 3. ActorFactory Integration

- [x] 3.1 Modify `metagpt/actor/actor_factory.py`'s `create_actor_for_task` method.
- [x] 3.2 Update LLM prompt within `ActorFactory` to include dynamically registered tools (both types) for tool recommendation.
- [x] 3.3 Implement logic in `ActorFactory` to retrieve recommended tools from `ToolRegistry`, regardless of their underlying type.
- [x] 3.4 Implement logic in `ActorFactory` to pass provisioned tools to the `Actor` instance.

## 4. Testing and Verification

- [x] 4.1 Create unit tests for `tool_loader.py` (tool discovery for both types, metadata extraction, LLM-prompt tool wrapping).
- [x] 4.2 Create unit tests for `ToolRegistry`'s new tool registration and duplicate handling for both tool types.
- [x] 4.3 Create unit tests for `ActorFactory`'s tool provisioning logic with diverse tool types.
- [x] 4.4 Create an integration test to verify end-to-end dynamic tool loading, registration, and actor usage for both Python callable and LLM-prompt-based tools.