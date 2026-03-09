import glob
import inspect
import importlib.util
import json
import logging # Added logging import
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from metagpt.tools.tool_data_type import Tool
from metagpt.utils.tool_registry import ToolMetadata
from metagpt.tools.tool_convert import convert_code_to_tool_schema
from metagpt.llm import LLM # Import LLM function
from metagpt.config2 import config # Import global config

logger = logging.getLogger(__name__) # Initialize logger

def discover_python_files(tool_dirs: List[Path]) -> List[Path]:
    """
    Discovers all Python files in the specified tool directories.
    """
    python_files = []
    for tool_dir in tool_dirs:
        if not tool_dir.exists(): # Added existence check and logging
            logger.warning(f"Tool directory not found: {tool_dir}")
            continue
        # Use glob to find all .py files recursively
        python_files.extend(Path(f) for f in glob.glob(str(tool_dir / "**/*.py"), recursive=True))
    return python_files

def discover_llm_tool_dirs(tool_dirs: List[Path]) -> List[Path]:
    """
    Discovers subdirectories containing config.json and prompt files for LLM-prompt-based tools.
    """
    llm_tool_dirs = []
    for tool_dir in tool_dirs:
        if not tool_dir.exists(): # Added existence check
            continue
        for subdir in tool_dir.glob("**/*"):
            if subdir.is_dir() and (subdir / "config.json").exists():
                # Check for any .txt file as a generic prompt file indicator
                if any(f.suffix == ".txt" for f in subdir.iterdir()):
                    llm_tool_dirs.append(subdir)
    return llm_tool_dirs

def _load_module_from_path(file_path: Path):
    """
    Loads a Python module from a given file path.
    """
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        try: # Added error handling for module execution
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Error loading module {module_name} from {file_path}: {e}")
    return None

def extract_tool_metadata_from_function(func: Callable) -> Optional[ToolMetadata]:
    """
    Extracts ToolMetadata from a callable function.
    Prioritizes explicit ToolMetadata objects, then docstrings, then type hints.
    """
    # 1. Check for explicit ToolMetadata attribute (e.g., assigned via a decorator)
    # This assumes a decorator or direct assignment adds a __tool_metadata__ attribute
    if hasattr(func, "__tool_metadata__") and isinstance(getattr(func, "__tool_metadata__"), ToolMetadata):
        return getattr(func, "__tool_metadata__")

    # 2. Parse from docstring (e.g., JSON in docstring)
    # This is a simplified example; a more robust parser might be needed
    if func.__doc__:
        try:
            # Look for a JSON block within the docstring, e.g., delimited by ```json ... ```
            docstring_content = func.__doc__.strip()
            if "```json" in docstring_content and "```" in docstring_content:
                json_start = docstring_content.find("```json") + len("```json")
                json_end = docstring_content.find("```", json_start)
                if json_start != -1 and json_end != -1:
                    metadata_str = docstring_content[json_start:json_end].strip()
                    metadata_dict = json.loads(metadata_str)

                    # Extract description from before or after the JSON block
                    description_lines = [line.strip() for line in docstring_content.split('\n') if line.strip() and not (line.strip().startswith("```json") or line.strip().startswith("```"))]
                    description = description_lines[0] if description_lines else f"A callable tool function: {func.__name__}"

                    return ToolMetadata(
                        name=metadata_dict.get("name", func.__name__),
                        description=metadata_dict.get("description", description),
                        usage_example=metadata_dict.get("usage_example", ""),
                        input_schema=metadata_dict.get("input_schema", {}),
                        output_schema=metadata_dict.get("output_schema", {}),
                        cost_model=metadata_dict.get("cost_model", ""),
                        access_requirements=metadata_dict.get("access_requirements", ""),
                        tool_function=func
                    )
        except json.JSONDecodeError as e: # Added specific error handling for JSON
            logger.warning(f"JSONDecodeError in docstring of {func.__name__}: {e}")
        except Exception as e: # Catch other potential errors
            logger.error(f"Error parsing docstring for {func.__name__}: {e}")


    # 3. Extract from type hints and function signature
    sig = inspect.signature(func)
    params: Dict[str, Any] = {}
    for name, param in sig.parameters.items():
        param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "Any"
        params[name] = {"type": param_type}
        if param.default != inspect.Parameter.empty:
            params[name]["default"] = str(param.default) # Convert default to string for schema representation

    return_type_str = sig.return_annotation.__name__ if sig.return_annotation != inspect.Parameter.empty else "Any"
    return_schema: Dict[str, Any] = {"type": return_type_str}

    # Fallback to function name and first line of docstring for description
    description = func.__doc__.split('\n')[0].strip() if func.__doc__ else f"A callable tool function: {func.__name__}"

    return ToolMetadata(
        name=func.__name__,
        description=description,
        input_schema=params,
        output_schema=return_schema,
        tool_function=func
    )

def discover_callable_tools_in_file(file_path: Path) -> List[ToolMetadata]:
    """
    Discovers callable functions and extracts ToolMetadata from a given Python file.
    """
    tools = []
    module = _load_module_from_path(file_path)
    if module:
        for name in dir(module):
            obj = getattr(module, name)
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                # Avoid loading internal/private functions by convention
                if not name.startswith("_"):
                    metadata = extract_tool_metadata_from_function(obj)
                    if metadata:
                        tools.append(metadata)
    return tools

def load_llm_tool(llm_tool_dir: Path) -> Optional[ToolMetadata]:
    """
    Parses config.json and prompt files for LLM-prompt-based tools
    and constructs their ToolMetadata, including a callable wrapper.
    """
    config_path = llm_tool_dir / "config.json"
    if not config_path.exists():
        logger.warning(f"config.json not found in LLM tool directory: {llm_tool_dir}")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            tool_config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding config.json in {llm_tool_dir}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading config.json in {llm_tool_dir}: {e}")
        return None

    # Find the prompt file
    prompt_file_path = None
    for f in llm_tool_dir.iterdir():
        if f.suffix == ".txt" and f.name != "config.json": # Assuming prompt files are .txt and not config.json
            prompt_file_path = f
            break

    if not prompt_file_path:
        logger.warning(f"No prompt file (.txt) found in LLM tool directory: {llm_tool_dir}")
        return None

    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except Exception as e:
        logger.error(f"Error reading prompt file {prompt_file_path}: {e}")
        return None

    name = tool_config.get("name", llm_tool_dir.name)
    description = tool_config.get("description", f"An LLM-prompt-based tool: {name}")
    input_schema = tool_config.get("input_schema", {})
    output_schema = tool_config.get("output_schema", {"type": "string"})
    llm_parameters = tool_config.get("llm_parameters", {})

    async def _llm_tool_wrapper(**kwargs):
        """Callable wrapper for LLM-prompt-based tools."""
        try:
            llm_instance = LLM(llm_config=config.llm)

            # Format the prompt using kwargs
            formatted_prompt = prompt_template.format(**kwargs)

            # Call the LLM
            # TODO: Pass llm_parameters to aask if supported and necessary
            response = await llm_instance.aask(formatted_prompt)
            return response
        except Exception as e:
            logger.error(f"Error executing LLM tool '{name}': {e}")
            raise

    # Create a ToolMetadata object
    return ToolMetadata(
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        tool_function=_llm_tool_wrapper,
        usage_example=tool_config.get("usage_example", ""),
        cost_model=tool_config.get("cost_model", ""),
        access_requirements=tool_config.get("access_requirements", "")
    )


def _adapt_old_tool_to_new_metadata(old_tool: 'Tool') -> List[ToolMetadata]:
    """
    Adapts an old-style Tool object into one or more new-style ToolMetadata objects.
    """
    # Handle function-based tools
    if old_tool.schemas and "function" in old_tool.schemas:
        func_name = old_tool.schemas["function"].get("name", old_tool.name)
        module = _load_module_from_path(Path(old_tool.path))
        if not module:
            return []
        func = getattr(module, func_name, None)

        if func and inspect.isfunction(func):
            # Use convert_code_to_tool_schema to get detailed schemas
            tool_schema_dict = convert_code_to_tool_schema(func)

            new_tools.append(ToolMetadata(
                name=old_tool.name,
                description=tool_schema_dict.get("description", old_tool.schemas.get("description", f"Old function tool: {old_tool.name}")),
                usage_example=tool_schema_dict.get("usage_example", ""),
                input_schema=tool_schema_dict.get("parameters", {}),
                output_schema=tool_schema_dict.get("returns", {}),
                tool_function=func
            ))
        else:
            logger.warning(f"Could not find callable function '{func_name}' for old tool '{old_tool.name}' in {old_tool.path}")

    # Handle class-based tools
    if old_tool.schemas and "methods" in old_tool.schemas:
        class_name = old_tool.schemas["class_name"]
        module = _load_module_from_path(Path(old_tool.path))
        if not module:
            return []
        ToolClass = getattr(module, class_name, None)

        if not ToolClass or not inspect.isclass(ToolClass):
            logger.warning(f"Could not find class '{class_name}' for old tool '{old_tool.name}' in {old_tool.path}")
        else:
            # Cache instance of the tool class
            tool_instance = ToolClass()

            for method_name, method_schema in old_tool.schemas["methods"].items():
                if method_name.startswith("_"): # Skip private methods
                    continue

                method_func = getattr(tool_instance, method_name, None)

                if not method_func or not (inspect.isfunction(method_func) or inspect.ismethod(method_func)):
                    logger.warning(f"Could not find method '{method_name}' in class '{class_name}' for old tool '{old_tool.name}'")
                    continue

                # Generate new ToolMetadata name for method
                new_tool_name = f"{old_tool.name.lower()}_{method_name}"

                # Extract description, input_schema, output_schema for the method
                sig = inspect.signature(method_func)
                input_schema_params = {}
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "Any"
                    input_schema_params[param_name] = {"type": param_type}
                    if param.default != inspect.Parameter.empty:
                        input_schema_params[param_name]["default"] = str(param.default) # Convert default to string for schema representation

                return_type_str = sig.return_annotation.__name__ if sig.return_annotation != inspect.Parameter.empty else "Any"
                output_schema_val = {"type": return_type_str}

                description = method_schema.get("description", f"Method '{method_name}' of tool '{old_tool.name}'")
                usage_example = method_schema.get("usage_example", "")

                # Create an async wrapper function
                async def _method_wrapper(**kwargs):
                    if inspect.iscoroutinefunction(method_func):
                        return await method_func(**kwargs)
                    else:
                        return method_func(**kwargs)

                new_tools.append(ToolMetadata(
                    name=new_tool_name,
                    description=description,
                    usage_example=usage_example,
                    input_schema=input_schema_params,
                    output_schema=output_schema_val,
                    tool_function=_method_wrapper
                )))
    return new_tools


