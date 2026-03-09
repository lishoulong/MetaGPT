## Why

The current MetaGPT architecture has two incompatible tool registration mechanisms, preventing the new dynamic Actor/Planner system from fully utilizing existing tools. This change is needed to unify the tool ecosystem and leverage new Actor/Planner capabilities effectively without high migration costs.

## What Changes

- Introduce an adapter layer in `metagpt/utils/tool_registry.py` to convert `Tool` objects registered via the old `metagpt/tools/tool_registry.py` into `ToolMetadata` objects expected by the new system.
- For class-based tools (e.g., `Browser`), create separate `ToolMetadata` entries for each callable method (e.g., `browser_type_text`, `browser_scroll_page`).
- The `tool_function` in the new `ToolMetadata` will wrap the invocation of the old tool's methods, handling instance creation and parameter mapping.
- Update `metagpt/utils/tool_registry.py`'s `load_and_register_all_tools` to integrate this adapter.

## Capabilities

### New Capabilities
- `unified-tool-registration`: Allows all tools, regardless of their original registration mechanism, to be discoverable and usable by the new Actor/Planner system through a single `ToolRegistry`.
- `old-tool-adapter`: Provides a mechanism to adapt existing `Tool` objects (especially class methods) into the `ToolMetadata` format expected by the new system.

### Modified Capabilities
- `tool-discovery`: The process of discovering and loading tools will be enhanced to include adaptation of old tools.
- `tool-selection`: The LLM-based tool selection in `actor_factory.py` will now have access to a broader set of tools.

## Impact

- `metagpt/utils/tool_registry.py`: Will be modified to include the adapter logic and load tools from the old registry.
- `metagpt/tools/tool_registry.py`: Will be utilized by the new adapter, but not directly modified.
- `metagpt/actor/actor_factory.py`: Will benefit from a richer set of discoverable tools due to expanded tool availability.
- Existing tools in `metagpt/tools/libs/` (e.g., `browser.py`): Will become compatible with the new Actor/Planner system without direct modification to their source files.
