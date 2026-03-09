import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

from metagpt.utils.tool_loader import (
    discover_python_files,
    discover_llm_tool_dirs,
    extract_tool_metadata_from_function,
    load_llm_tool,
)
from metagpt.utils.tool_registry import ToolMetadata
from metagpt.configs.llm_config import LLMConfig
from metagpt.config2 import config # For mocking METAGPT_ROOT if needed

# Mock the global config for tool_dirs for testing purposes
@pytest.fixture(autouse=True)
def mock_config_fixture():
    with patch('metagpt.config2.config') as mock_cfg:
        mock_cfg.llm = LLMConfig() # Provide a default LLMConfig
        mock_cfg.tool_dirs = [] # Default to empty for controlled tests
        yield mock_cfg

@pytest.fixture
def temp_tool_base_dir(tmp_path, mock_config_fixture):
    """Fixture to create a temporary base directory for tool discovery tests."""
    temp_tools_dir = tmp_path / "tools_base"
    temp_tools_dir.mkdir()
    mock_config_fixture.tool_dirs = [temp_tools_dir]
    yield temp_tools_dir

@pytest.fixture
def temp_llm_tool_dir(tmp_path):
    """Fixture to create a temporary directory for LLM tool tests."""
    llm_tool_path = tmp_path / "llm_tool_example"
    llm_tool_path.mkdir()
    (llm_tool_path / "config.json").write_text('{"name": "test_llm_tool", "description": "A test LLM tool", "input_schema": {"query": {"type": "string"}}}')
    (llm_tool_path / "prompt.txt").write_text("Hello {query}")
    yield llm_tool_path

class TestToolLoader:
    def test_discover_python_files(self, temp_tool_base_dir, mock_config_fixture):
        # Test basic discovery
        tool_dir = temp_tool_base_dir / "sub_tools_1"
        tool_dir.mkdir()
        (tool_dir / "tool_a.py").write_text("def func_a(): pass")
        (tool_dir / "nested").mkdir()
        (tool_dir / "nested" / "tool_b.py").write_text("def func_b(): pass")

        skills_dir = temp_tool_base_dir / "sub_skills_1"
        skills_dir.mkdir()
        (skills_dir / "skill_c.py").write_text("def func_c(): pass")

        mock_config_fixture.tool_dirs = [tool_dir, skills_dir]

        found_files = discover_python_files(mock_config_fixture.tool_dirs)
        expected_files = {
            tool_dir / "tool_a.py",
            tool_dir / "nested" / "tool_b.py",
            skills_dir / "skill_c.py",
        }
        assert len(found_files) == len(expected_files)
        assert set(found_files) == expected_files

        # Test with empty directories
        shutil.rmtree(tool_dir)
        tool_dir.mkdir()
        shutil.rmtree(skills_dir)
        skills_dir.mkdir()
        found_files = discover_python_files(mock_config_fixture.tool_dirs)
        assert not found_files

    def test_discover_llm_tool_dirs(self, temp_tool_base_dir, mock_config_fixture):
        tools_dir = temp_tool_base_dir

        # Valid LLM tool dir
        valid_llm_tool_dir = tools_dir / "llm_tool_1"
        valid_llm_tool_dir.mkdir()
        (valid_llm_tool_dir / "config.json").write_text("{}")
        (valid_llm_tool_dir / "prompt.txt").write_text("prompt")

        # LLM tool dir missing config.json
        missing_config_dir = tools_dir / "llm_tool_2"
        missing_config_dir.mkdir()
        (missing_config_dir / "prompt.txt").write_text("prompt")

        # LLM tool dir missing prompt.txt
        missing_prompt_dir = tools_dir / "llm_tool_3"
        missing_prompt_dir.mkdir()
        (missing_prompt_dir / "config.json").write_text("{}")

        # Nested valid LLM tool dir
        nested_llm_tool_dir = tools_dir / "nested" / "llm_tool_4"
        nested_llm_tool_dir.mkdir(parents=True)
        (nested_llm_tool_dir / "config.json").write_text("{}")
        (nested_llm_tool_dir / "template.txt").write_text("template") # Test with a different .txt name

        mock_config_fixture.tool_dirs = [tools_dir]
        found_dirs = discover_llm_tool_dirs(mock_config_fixture.tool_dirs)
        expected_dirs = {valid_llm_tool_dir, nested_llm_tool_dir}

        assert len(found_dirs) == len(expected_dirs)
        assert set(found_dirs) == expected_dirs

        # Test with empty directory
        shutil.rmtree(tools_dir)
        tools_dir.mkdir()
        found_dirs = discover_llm_tool_dirs(mock_config_fixture.tool_dirs)
        assert not found_dirs

    @pytest.mark.asyncio
    async def test_adapt_old_tool_to_new_metadata_function_tool(self):
        # 1. Mock the old Tool object for a function-based tool
        mock_tool_path = "/path/to/mock_module.py"
        mock_old_tool = MagicMock(spec=Tool)
        mock_old_tool.name = "mock_function_tool"
        mock_old_tool.path = mock_tool_path
        mock_old_tool.schemas = {
            "function": {
                "name": "mocked_func",
                "description": "A mocked function tool.",
                "parameters": {"type": "object", "properties": {"arg1": {"type": "string"}}},
                "returns": {"type": "object", "properties": {"result": {"type": "boolean"}}}
            }
        }

        # 2. Mock the actual function that _adapt_old_tool_to_new_metadata will try to find
        def mocked_func(arg1: str) -> bool:
            """A mocked function tool."""
            return arg1 == "test"
        # mocked_func.__doc__ = "A mocked function tool." # Ensure docstring is present for extract_tool_metadata_from_function

        # 3. Mock _load_module_from_path to return a module containing our mocked function
        mock_module = MagicMock()
        mock_module.mocked_func = mocked_func
        with patch('metagpt.utils.tool_loader._load_module_from_path', return_value=mock_module):
            # 4. Call the function under test
            adapted_tools = _adapt_old_tool_to_new_metadata(mock_old_tool)

            # 5. Assertions
            assert len(adapted_tools) == 1
            tool_meta = adapted_tools[0]
            assert isinstance(tool_meta, ToolMetadata)
            assert tool_meta.name == "mock_function_tool" # Old tool name is used
            assert tool_meta.description == "A mocked function tool."
            assert tool_meta.input_schema == {"arg1": {"type": "str"}} # From inspect.signature
            assert tool_meta.output_schema == {"type": "bool"} # From inspect.signature
            assert tool_meta.tool_function == mocked_func

    @pytest.mark.asyncio
    async def test_adapt_old_tool_to_new_metadata_class_tool(self):
        # 1. Mock the old Tool object for a class-based tool
        mock_tool_path = "/path/to/mock_class_module.py"
        mock_old_tool = MagicMock(spec=Tool)
        mock_old_tool.name = "MockClassTool"
        mock_old_tool.path = mock_tool_path
        mock_old_tool.schemas = {
            "class_name": "MockToolClass",
            "methods": {
                "sync_method": {
                    "description": "A synchronous method.",
                    "parameters": {"type": "object", "properties": {"param_s": {"type": "integer"}}},
                    "returns": {"type": "object", "properties": {"result": {"type": "string"}}}
                },
                "async_method": {
                    "description": "An asynchronous method.",
                    "parameters": {"type": "object", "properties": {"param_a": {"type": "boolean"}}},
                    "returns": {"type": "object", "properties": {"status": {"type": "string"}}}
                }
            }
        }

        # 2. Mock the actual class and its methods
        class MockToolClass:
            def sync_method(self, param_s: int) -> str:
                return f"Sync result: {param_s}"

            async def async_method(self, param_a: bool) -> str:
                return f"Async status: {param_a}"

        # 3. Mock _load_module_from_path to return a module containing our mocked class
        mock_module = MagicMock()
        mock_module.MockToolClass = MockToolClass
        with patch('metagpt.utils.tool_loader._load_module_from_path', return_value=mock_module):
            # 4. Call the function under test
            adapted_tools = _adapt_old_tool_to_new_metadata(mock_old_tool)

            # 5. Assertions
            assert len(adapted_tools) == 2

            # Check sync_method
            sync_tool_meta = next(t for t in adapted_tools if t.name == "mockclasstool_sync_method")
            assert isinstance(sync_tool_meta, ToolMetadata)
            assert sync_tool_meta.description == "A synchronous method."
            assert sync_tool_meta.input_schema == {"param_s": {"type": "int"}}
            assert sync_tool_meta.output_schema == {"type": "str"}
            # Test the callable wrapper
            sync_result = sync_tool_meta.tool_function(param_s=123)
            assert sync_result == "Sync result: 123"

            # Check async_method
            async_tool_meta = next(t for t in adapted_tools if t.name == "mockclasstool_async_method")
            assert isinstance(async_tool_meta, ToolMetadata)
            assert async_tool_meta.description == "An asynchronous method."
            assert async_tool_meta.input_schema == {"param_a": {"type": "bool"}}
            assert async_tool_meta.output_schema == {"type": "str"}
            # Test the callable wrapper
            async_result = await async_tool_meta.tool_function(param_a=True)
            assert async_result == "Async status: True"

    def test_extract_tool_metadata_from_function_explicit(self):
        meta = ToolMetadata(name="explicit_tool", description="Explicit desc", tool_function=lambda: None)
        def my_func_explicit():
            pass
        my_func_explicit.__tool_metadata__ = meta

        result = extract_tool_metadata_from_function(my_func_explicit)
        assert result == meta
        assert result.name == "explicit_tool"

    def test_extract_tool_metadata_from_function_docstring(self):
        def my_func_docstring(param1: str, param2: int = 1):
            """
            ```json
            {
                "name": "docstring_tool",
                "description": "Docstring description.",
                "input_schema": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
                "output_schema": {"type": "boolean"}
            }
            ```
            This is a more detailed explanation.
            """
            pass
        result = extract_tool_metadata_from_function(my_func_docstring)
        assert result is not None
        assert result.name == "docstring_tool"
        assert result.description == "Docstring description."
        assert result.input_schema == {"param1": {"type": "string"}, "param2": {"type": "integer"}}
        assert result.output_schema == {"type": "boolean"}
        assert result.tool_function == my_func_docstring

    def test_extract_tool_metadata_from_function_type_hints(self):
        def my_func_type_hints(name: str, age: int) -> bool:
            """A function with type hints."""
            return True

        result = extract_tool_metadata_from_function(my_func_type_hints)
        assert result is not None
        assert result.name == "my_func_type_hints"
        assert result.description == "A function with type hints."
        assert result.input_schema == {"name": {"type": "str"}, "age": {"type": "int"}}
        assert result.output_schema == {"type": "bool"}
        assert result.tool_function == my_func_type_hints

    @pytest.mark.asyncio
    async def test_load_llm_tool(self, temp_llm_tool_dir, mock_config_fixture):
        # Mock the LLM aask method
        mock_llm_instance = AsyncMock()
        mock_llm_instance.aask.return_value = "LLM response for query."
        with patch('metagpt.llm.LLM', return_value=mock_llm_instance) as mock_llm_constructor:
            # Ensure config.llm is set for the mock
            mock_config_fixture.llm = LLMConfig()

            tool_metadata = load_llm_tool(temp_llm_tool_dir)

            assert tool_metadata is not None
            assert tool_metadata.name == "test_llm_tool"
            assert tool_metadata.description == "A test LLM tool"
            assert tool_metadata.input_schema == {"query": {"type": "string"}}

            # Test the callable wrapper
            result = await tool_metadata.tool_function(query="test query")

            mock_llm_constructor.assert_called_once_with(llm_config=mock_config_fixture.llm)
            mock_llm_instance.aask.assert_called_once_with("Hello test query")
            assert result == "LLM response for query."

    @pytest.mark.asyncio
    async def test_load_llm_tool_missing_config_or_prompt(self, tmp_path):
        # Test missing config.json
        missing_config_dir = tmp_path / "no_config"
        missing_config_dir.mkdir()
        (missing_config_dir / "prompt.txt").write_text("prompt")
        assert load_llm_tool(missing_config_dir) is None

        # Test missing prompt.txt
        missing_prompt_dir = tmp_path / "no_prompt"
        missing_prompt_dir.mkdir()
        (missing_prompt_dir / "config.json").write_text("{}")
        assert load_llm_tool(missing_prompt_dir) is None
