## 1. Environment Setup and Old Tool Registry Access

- [x] 1.1 Import `metagpt.tools.tool_registry.TOOL_REGISTRY` into `metagpt/utils/tool_registry.py`.
- [x] 1.2 Import `metagpt.tools.tool_data_type.Tool` into `metagpt/utils/tool_registry.py`.
- [x] 1.3 Import `metagpt.tools.tool_convert.convert_code_to_tool_schema` into `metagpt/utils/tool_loader.py` for schema extraction.

## 2. Implement Old Tool Adapter Logic

- [x] 2.1 Create a new function `_adapt_old_tool_to_new_metadata` in `metagpt/utils/tool_loader.py` that takes an old `Tool` object and returns a list of `ToolMetadata` objects.
- [x] 2.2 Inside `_adapt_old_tool_to_new_metadata`, handle ordinary function `Tool` objects:
    - [x] 2.2.1 Extract `name`, `description`, `input_schema`, `output_schema` from the old `Tool` object.
    - [x] 2.2.2 Set `tool_function` to the actual callable object from the old `Tool`'s code (requires reflection/import).
- [x] 2.3 Inside `_adapt_old_tool_to_new_metadata`, handle class-based `Tool` objects:
    - [x] 2.3.1 Create a mechanism to instantiate the old tool class once (e.g., `Browser`). Store this instance.
    - [x] 2.3.2 For each method in `old_tool.schemas["methods"]`:
        - [x] 2.3.2.1 Construct a `ToolMetadata.name` as `f"{old_tool.name.lower()}_{method_name}"`.
        - [x] 2.3.2.2 Extract `description`, `input_schema`, `output_schema` for the method.
        - [x] 2.3.2.3 Create an `async` wrapper function as `ToolMetadata.tool_function` that calls the corresponding method on the cached instance.
- [x] 2.4 Ensure correct parameter mapping from the `Actor`'s `**kwargs` to the adapted tool method's arguments.

## 3. Integrate Adapter into `load_and_register_all_tools`

- [x] 3.1 In `metagpt/utils/tool_registry.py`'s `load_and_register_all_tools` function, iterate through `OLD_TOOL_REGISTRY`.
- [x] 3.2 For each `Tool` object found in `OLD_TOOL_REGISTRY`, call `_adapt_old_tool_to_new_metadata` to get a list of `ToolMetadata` objects.
- [x] 3.3 Register each resulting `ToolMetadata` object with the new `ToolRegistry`.

## 4. Testing and Verification

- [x] 4.1 Write a unit test for `_adapt_old_tool_to_new_metadata` using a mock `Tool` object.
- [x] 4.2 Write an integration test to ensure `Browser` methods (e.g., `browser_type_text`, `browser_scroll_page`) are correctly discovered and callable through the new `ToolRegistry`.
- [x] 4.3 Verify that `ActorFactory` can recommend and `Actor` can execute adapted `Browser` methods.
