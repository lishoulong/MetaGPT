## ADDED Requirements

### Requirement: Tool Discovery Mechanism
The system SHALL provide a mechanism to discover various types of tools from configurable directories.
The discovery mechanism SHALL identify Python files (e.g., `.py`) and tool definition directories (e.g., containing `config.json` and a prompt file) within the specified directories and their subdirectories.
Each discovered tool SHALL be expected to conform to a recognizable structure for metadata extraction.

#### Scenario: Discover Python callable tools
- **WHEN** the tool discovery mechanism is invoked with a valid directory path
- **THEN** all Python files within that directory and its subdirectories are identified as potential Python callable tool sources (e.g., existing utilities, new Python skills)

#### Scenario: Discover LLM-prompt-based tools
- **WHEN** the tool discovery mechanism is invoked with a valid directory path
- **THEN** subdirectories containing `config.json` and a prompt file (e.g., `skprompt.txt`) are identified as potential LLM-prompt-based tool sources

#### Scenario: Ignore irrelevant files and directories
- **WHEN** the tool discovery mechanism is invoked on a directory containing files or subdirectories that do not conform to Python callable or LLM-prompt-based tool structures
- **THEN** these irrelevant items are ignored, and only valid tool sources are considered

### Requirement: Tool Metadata Extraction
The system SHALL extract metadata from discovered tool sources to enable their registration.
The extracted metadata SHALL include the tool's name, description, usage example, and input schema.
The system SHALL support different methods of metadata extraction based on the tool type:
- For Python callable tools: `ToolMetadata` objects, function annotations, or docstrings.
- For LLM-prompt-based tools: `config.json` content.

#### Scenario: Extract metadata from a Python callable tool
- **WHEN** a Python file contains a `ToolMetadata` object or a function with type hints/docstrings
- **THEN` the tool's name, description, usage example, and input schema are correctly extracted

#### Scenario: Extract metadata from an LLM-prompt-based tool
- **WHEN** a tool definition directory contains a `config.json` with a `description` and `input.parameters`
- **THEN` the tool's name (derived from directory name), description, and input schema are correctly extracted from the `config.json`

#### Scenario: Handle missing or invalid metadata gracefully
- **WHEN** a discovered tool source lacks complete or valid metadata
- **THEN` the discovery mechanism SHALL log a warning and either use default values, attempt inference, or skip the tool, depending on configuration and strictness

### Requirement: Internal Utility Tools for Integration

The system SHALL integrate the following identified internal utility functions and classes as discoverable tools, making them accessible to agents for various tasks. These tools provide specialized capabilities that enhance the system's overall functionality.

#### Tool Group: OmniParse Client (`metagpt/utils/omniparse_client.py`)
Provides capabilities for parsing various media and document types via an OmniParse server.

##### Tool: `omniparse_document`
- **Description**: Parses general document content using an OmniParse server, returning structured data.
- **Function Signature (Example)**: `async def parse_document(self, document_content: str, file_type: str, **kwargs) -> Dict`
- **Parameters**:
    - `document_content` (str): **Required**. The string representation of the document content to be parsed.
    - `file_type` (str): **Required**. The type of the document (e.g., "docx", "txt", "md").
    - `kwargs` (dict, optional): **Optional**. Additional keyword arguments to pass to the OmniParse API.
- **Return Value**: `Dict` - A dictionary containing the parsed document data.

##### Tool: `omniparse_pdf`
- **Description**: Parses PDF document content using an OmniParse server, returning structured data.
- **Function Signature (Example)**: `async def parse_pdf(self, pdf_content: bytes, **kwargs) -> Dict`
- **Parameters**:
    - `pdf_content` (bytes): **Required**. The byte content of the PDF file.
    - `kwargs` (dict, optional): **Optional**. Additional keyword arguments to pass to the OmniParse API.
- **Return Value**: `Dict` - A dictionary containing the parsed PDF data.

##### Tool: `omniparse_video`
- **Description**: Parses video content or links via an OmniParse server, returning structured data (e.g., video transcription, scene analysis).
- **Function Signature (Example)**: `async def parse_video(self, video_source: str, **kwargs) -> Dict`
- **Parameters**:
    - `video_source` (str): **Required**. The URL of the video or an identifier for its content.
    - `kwargs` (dict, optional): **Optional**. Additional keyword arguments to pass to the OmniParse API.
- **Return Value**: `Dict` - A dictionary containing the parsed video data.

##### Tool: `omniparse_audio`
- **Description**: Parses audio content or links via an OmniParse server, returning structured data (e.g., audio transcription).
- **Function Signature (Example)**: `async def parse_audio(self, audio_source: str, **kwargs) -> Dict`
- **Parameters**:
    - `audio_source` (str): **Required**. The URL of the audio or an identifier for its content.
    - `kwargs` (dict, optional): **Optional**. Additional keyword arguments to pass to the OmniParse API.
- **Return Value**: `Dict` - A dictionary containing the parsed audio data.

#### Tool Group: S3 Storage (`metagpt/utils/s3.py`)
Provides capabilities for interacting with Amazon S3 storage service.

##### Tool: `s3_upload_file`
- **Description**: Uploads a local file to a specified Amazon S3 bucket and key.
- **Function Signature (Example)**: `async def upload_file(self, local_path: Path, bucket_name: str, s3_key: str) -> str`
- **Parameters**:
    - `local_path` (Path): **Required**. The path to the local file.
    - `bucket_name` (str): **Required**. The name of the S3 bucket.
    - `s3_key` (str): **Required**. The key (full path) for the object in S3.
- **Return Value**: `str` - The URL of the S3 object after upload.

##### Tool: `s3_download_file`
- **Description**: Downloads a file from a specified Amazon S3 bucket and key to a local path.
- **Function Signature (Example)**: `async def download_file(self, bucket_name: str, s3_key: str, local_path: Path) -> str`
- **Parameters**:
    - `bucket_name` (str): **Required**. The name of the S3 bucket.
    - `s3_key` (str): **Required**. The key (full path) for the object in S3.
    - `local_path` (Path): **Required**. The local path where the file should be saved.
- **Return Value**: `str` - The local path of the downloaded file.

##### Tool: `s3_get_object_url`
- **Description**: Retrieves a pre-signed or public URL for an object stored in Amazon S3.
- **Function Signature (Example)**: `async def get_object_url(self, bucket_name: str, s3_key: str, expires_in: int = 3600) -> str`
- **Parameters**:
    - `bucket_name` (str): **Required**. The name of the S3 bucket.
    - `s3_key` (str): **Required**. The key (full path) for the object in S3.
    - `expires_in` (int, optional): **Optional**. Expiration time for the pre-signed URL in seconds. Default: 3600.
- **Return Value**: `str` - The URL of the S3 object.

##### Tool: `s3_cache_data`
- **Description**: Caches data to Amazon S3, typically for temporary storage or sharing.
- **Function Signature (Example)**: `async def cache_data(self, data: bytes, bucket_name: str, s3_key: str) -> str`
- **Parameters**:
    - `data` (bytes): **Required**. The byte data to be cached.
    - `bucket_name` (str): **Required**. The name of the S3 bucket.
    - `s3_key` (str): **Required**. The key (full path) for the object in S3.
- **Return Value**: `str` - The S3 key of the cached object.

#### Tool Group: Mermaid Diagram Generation (`metagpt/utils/mermaid.py`, `mmdc_ink.py`, `mmdc_playwright.py`, `mmdc_pyppeteer.py`)
Converts Mermaid code into image, SVG, or PDF formats using various rendering backends.

##### Tool: `mermaid_to_file`
- **Description**: Renders Mermaid flowchart/sequence diagram code into an image file (PNG, SVG, PDF). Specific implementations may rely on different renderers like `mmdc_ink`, `mmdc_playwright`, `mmdc_pyppeteer`.
- **Function Signature (Example)**: `async def mermaid_to_file(content: str, output_file: Path, width: Optional[int] = None, height: Optional[int] = None, renderer: str = "playwright") -> Path`
- **Parameters**:
    - `content` (str): **Required**. The Mermaid diagram code.
    - `output_file` (Path): **Required**. The path and name of the output file (e.g., "output.png", "output.svg", "output.pdf").
    - `width` (int, optional): **Optional**. The width of the output image.
    - `height` (int, optional): **Optional**. The height of the output image.
    - `renderer` (str, optional): **Optional**. Specifies the renderer type to use, e.g., "ink", "playwright", "pyppeteer". Default: "playwright".
- **Return Value**: `Path` - The path to the generated output file.

#### Tool Group: Document Reader (`metagpt/utils/read_document.py`)
Specialized for reading `.docx` files.

##### Tool: `read_docx`
- **Description**: Parses the content of a Microsoft Word `.docx` file and returns its plain text.
- **Function Signature (Example)**: `async def read_docx(file_path: Path) -> str`
- **Parameters**:
    - `file_path` (Path): **Required**. The path to the `.docx` file.
- **Return Value**: `str` - The plain text content of the document.

#### Tool Group: HTML Content Processor (`metagpt/utils/parse_html.py`)
Provides functions for processing web page content.

##### Tool: `simplify_html`
- **Description**: Removes unnecessary tags and attributes from an HTML string to obtain cleaner text content.
- **Function Signature (Example)**: `def simplify_html(html_content: str) -> str`
- **Parameters**:
    - `html_content` (str): **Required**. The raw HTML string.
- **Return Value**: `str` - The simplified HTML string.

##### Tool: `get_html_content`
- **Description**: Fetches the full HTML content of a webpage given its URL.
- **Function Signature (Example)**: `async def get_html_content(url: str) -> str`
- **Parameters**:
    - `url` (str): **Required**. The URL of the webpage.
- **Return Value**: `str` - The HTML content of the webpage.

#### Tool Group: JSON to Markdown Converter (`metagpt/utils/json_to_markdown.py`)
Converts JSON objects into Markdown format.

##### Tool: `json_to_markdown`
- **Description**: Converts a Python dictionary or list (JSON object) into a readable Markdown formatted string.
- **Function Signature (Example)**: `def json_to_markdown(json_data: Dict | List) -> str`
- **Parameters**:
    - `json_data` (Dict | List): **Required**. The JSON data to convert.
- **Return Value**: `str` - The Markdown formatted string.

#### Tool Group: Repo to Markdown Converter (`metagpt/utils/repo_to_markdown.py`)
Converts a local code repository's structure and file content to Markdown format.

##### Tool: `repo_to_markdown`
- **Description**: Traverses a specified local code repository and generates a Markdown string containing the directory structure and content of specified files.
- **Function Signature (Example)**: `async def repo_to_markdown(repo_path: Path, include_patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None) -> str`
- **Parameters**:
    - `repo_path` (Path): **Required**. The path to the local code repository.
    - `include_patterns` (List[str], optional): **Optional**. A list of file patterns (e.g., `["*.py", "*.js"]`) to include in the Markdown.
    - `exclude_patterns` (List[str], optional): **Optional**. A list of file patterns to exclude from the Markdown.
- **Return Value**: `str` - A Markdown string containing the repository structure and file contents.

#### Tool Group: Visual Graph Repo (`metagpt/utils/visual_graph_repo.py`)
The `VisualDiGraphRepo` class provides methods to visualize class and sequence diagrams from graph data.

##### Tool: `visual_graph_class_view`
- **Description**: Generates a Mermaid class diagram code block for all classes from graph repository data.
- **Function Signature (Example)**: `async def get_mermaid_class_view(self) -> str`
- **Parameters**: None.
- **Return Value**: `str` - The Mermaid class diagram Markdown code.

##### Tool: `visual_graph_sequence_views`
- **Description**: Retrieves all Mermaid sequence diagrams and their corresponding graph repository keys from graph repository data.
- **Function Signature (Example)**: `async def get_mermaid_sequence_views(self) -> List[tuple[str, str]]`
- **Parameters**: None.
- **Return Value**: `List[tuple[str, str]]` - A list of `(key, sequence_diagram_code)` tuples.

#### Tool Group: Browser Automation / Accessibility Tree Interaction (`metagpt/utils/a11y_tree.py`)
Provides functionalities for browser operations and interacting with the accessibility tree.

##### Tool: `get_accessibility_tree`
- **Description**: Retrieves the accessibility tree structure of the current browser page, useful for analyzing page layout and elements.
- **Function Signature (Example)**: `async def get_accessibility_tree() -> Dict`
- **Parameters**: None.
- **Return Value**: `Dict` - A JSON or dictionary representation of the accessibility tree.

##### Tool: `execute_browser_step`
- **Description**: Executes a browser step (e.g., click, type, scroll) based on a given action and target.
- **Function Signature (Example)**: `async def execute_step(action: str, target: Dict, value: Optional[str] = None) -> Dict`
- **Parameters**:
    - `action` (str): **Required**. The type of action to perform (e.g., "click", "type", "scroll").
    - `target` (Dict): **Required**. A descriptor for the target element (e.g., containing "node_id", "selector").
    - `value` (str, optional): **Optional**. A value associated with the action (e.g., text to type).
- **Return Value**: `Dict` - The result of the operation.

##### Tool: `browser_click_element`
- **Description**: Clicks an element on the browser page based on its descriptor.
- **Function Signature (Example)**: `async def click_element(target: Dict) -> Dict`
- **Parameters**:
    - `target` (Dict): **Required**. A descriptor for the target element (e.g., containing "node_id", "selector").
- **Return Value**: `Dict` - The result of the operation.

##### Tool: `browser_type_text`
- **Description**: Types text into a specified element on the browser page.
- **Function Signature (Example)**: `async def type_text(target: Dict, text: str) -> Dict`
- **Parameters**:
    - `target` (Dict): **Required**. A descriptor for the target element.
    - `text` (str): **Required**. The text to type.
- **Return Value**: `Dict` - The result of the operation.

##### Tool: `browser_scroll_page`
- **Description**: Scrolls the current browser page.
- **Function Signature (Example)**: `async def scroll_page(direction: str, amount: Optional[int] = None) -> Dict`
- **Parameters**:
    - `direction` (str): **Required**. The scrolling direction (e.g., "up", "down", "left", "right").
    - `amount` (int, optional): **Optional**. The amount to scroll (in pixels or pages).
- **Return Value**: `Dict` - The result of the operation.

##### Tool: `browser_key_press`
- **Description**: Simulates a keyboard key press in the browser.
- **Function Signature (Example)**: `async def key_press(key: str) -> Dict`
- **Parameters**:
    - `key` (str): **Required**. The key to press (e.g., "Enter", "Escape", "Tab").
- **Return Value**: `Dict` - The result of the operation.

#### Tool Group: Directory Tree Visualization (`metagpt/utils/tree.py`)
Implements functionality similar to the `tree` command.

##### Tool: `directory_tree_viewer`
- **Description**: Recursively traverses and displays the directory structure in a tree-like format.
- **Function Signature (Example)**: `async def tree(root: Path, gitignore: Optional[Path] = None, run_command: bool = False) -> str`
- **Parameters**:
    - `root` (Path): **Required**. The root directory from which to start traversal.
    - `gitignore` (Path, optional): **Optional**. The path to a `.gitignore` file for filtering files.
    - `run_command` (bool, optional): **Optional**. Whether to execute the `tree` command-line tool. If `True`, the command output is returned; otherwise, a Python implementation is used. Default: `False`.
- **Return Value**: `str` - A string representation of the directory tree.

#### Tool Group: Asynchronous Helper (`metagpt/utils/async_helper.py`)
Provides functionality to run coroutines in a new event loop.

##### Tool: `run_async_in_new_loop`
- **Description**: Runs a given coroutine function in a fresh asyncio event loop and waits for its completion.
- **Function Signature (Example)**: `def run_coroutine_in_new_loop(coroutine_func: Callable, *args, **kwargs) -> Any`
- **Parameters**:
    - `coroutine_func` (Callable): **Required**. The coroutine function to run.
    - `*args`, `**kwargs`: **Optional**. Arbitrary positional and keyword arguments to pass to the coroutine function.
- **Return Value**: `Any` - The return value of the coroutine function.
