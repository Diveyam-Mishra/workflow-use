---
description: 
globs: 
alwaysApply: true
---
## 🧠 General Guidelines for Contributing to `browser-use`

**Browser-Use** is an AI agent that autonomously interacts with the web. It takes a user-defined task, navigates web pages using Chromium via Playwright, processes HTML, and repeatedly queries a language model (like `gpt-4o`) to decide the next action—until the task is completed.

### 🗂️ File Documentation

When you create a **new file**:

* **For humans**: At the top of the file, include a docstring in natural language explaining:

  * What this file does.
  * How it fits into the browser-use system.
  * If it introduces a new abstraction or replaces an old one.
* **For LLMs/AI**: Include structured metadata using standardized comments such as:

  ```python
  # @file purpose: Defines <purpose>
  ```

---

### 🧰 Development Rules

* ✅ **Always use [`uv`](mdc:https:/github.com/astral-sh/uv) instead of `pip`**
  For deterministic and fast dependency installs.

```bash
uv venv --python 3.11
source .venv/bin/activate
uv sync
```

* ✅ **Use real model names**
  Do **not** replace `gpt-4o` with `gpt-4`. The model `gpt-4o` is a distinct release and supported.

* ✅ **Type-safe coding**
  Use **Pydantic v2 models** for all internal action schemas, task inputs/outputs, and controller I/O. This ensures robust validation and LLM-call integrity.

* ✅ **Pre-commit formatting**
ALWAYS make sure to run pre-commit before making PRs.
---

## ⚙️ Adding New Actions

To add a new action that your browser agent can execute:

```python
from playwright.async_api import Page
from browser_use.core.controller import Controller, ActionResult

controller = Controller()

@controller.registry.action("Search the web for a specific query")
async def search_web(query: str, page: Page):
    # Implement your logic here, e.g., query a search engine and return results
    result = ...
    return ActionResult(extracted_content=result, include_in_memory=True)
```

### Notes:

* Use descriptive names and docstrings for each action.
* Prefer returning `ActionResult` with structured content to help the agent reason better.

---

## 🧠 Creating and Running an Agent

To define a task and run a browser-use agent:

```python
from browser_use import Agent
from browser_use.llm import ChatOpenAI

task = "Find the CEO of OpenAI and return their name"
model = ChatOpenAI(model="gpt-4.1-mini")

agent = Agent(task=task, llm=model, controller=controller)

history = await agent.run()
```

# Never create random examples

When I ask you to implement a feature never create new files that show off that feature -> the code just gets messy. If you do anything to test it out, just do the inline code inside the terminal (if you want).

# Problems we are dealing 
when i click on a button that opens a new tab, the workflow recording gets stuck and the window keeps loading and the event is not tracked
I was trying out this library, I am planning to use this as Test Automation Tool. But I don't see any option for assertion. Could you someone please help?
		images_used = 0
		for step in input_workflow.steps:
			step_messages: List[Dict[str, Any]] = []  # Messages for this specific step

			step_dict = step.model_dump(mode='json', exclude_none=True)
			step_type = getattr(step, 'type', step_dict.get('type'))
			step_url = getattr(step, 'url', step_dict.get('url', ''))
			# Skip steps to avoid processing empty or irrelevant navigation steps, mostly from iframes.
			if step_type == 'navigation' and step_url == 'about:blank':
				continue

			# 1. Text representation (JSON dump)
			screenshot_data = step_dict.pop('screenshot', None)  # Pop potential screenshot
			step_messages.append({'type': 'text', 'text': json.dumps(step_dict, indent=2)})

			# 2. Optional screenshot
			attach_image = use_screenshots and images_used < max_images		
This is still not working when made these changes to record iframes I frame capturing is not working 
A lot of times the variables are not being recorded as variables Also these llm calls i dont think they are working 
# Developers README for Workflow Backend

This document provides a comprehensive overview of the workflow backend, its architecture, and the role of each component. It is intended to help developers understand the system and contribute effectively.

## Project Goals

The primary goal of this project is to create a robust and scalable backend service for managing and executing automated workflows. These workflows can involve a variety of tasks, including web browser automation and interactions with large language models (LLMs). The system is designed to be flexible, allowing for the dynamic creation, modification, and execution of complex workflows.

## Architecture Overview

The backend is built using FastAPI, a modern, high-performance Python web framework. It follows a layered architecture that separates concerns into distinct components:

-   **API Layer (`api.py`)**: The main entry point for the application.
-   **Routing Layer (`routers.py`)**: Defines the API endpoints and handles incoming requests.
-   **Service Layer (`service.py`)**: Contains the core business logic for managing and executing workflows.
-   **Data Views (`views.py`)**: Defines the data structures (Pydantic models) used for API requests and responses.

This separation of concerns makes the codebase easier to understand, maintain, and test.

## Workflow Lifecycle and Detailed Architecture

While the backend provides the API for management, the core logic of creating and running workflows resides in the `workflow_use` package. The lifecycle consists of three main phases: Recording, Building, and Execution.

### 1. Recording Phase (`recorder` module)

This is the initial phase where a user's actions are captured to create a raw workflow.

-   **Mechanism**: The `RecordingService` starts a new browser session with a special **browser extension** loaded.
-   **Event Capture**: The extension monitors user interactions (clicks, typing, navigation) and sends this data as a series of events to a local web server run by the `RecordingService`.
-   **Output**: When the recording stops, the service compiles these events into a raw JSON file. This file is a simple, linear log of everything the user did.

### 2. Building Phase (`builder` module)

This phase transforms the raw recording into a smart, executable workflow using a Large Language Model (LLM).

-   **Mechanism**: The `BuilderService` takes the raw JSON recording, a high-level user goal (e.g., "Log in to the website and navigate to the dashboard"), and screenshots from the recording session.
-   **The Role of the LLM**: The service sends all of this context to an LLM. It asks the LLM to analyze the raw steps and the user's goal to create a more robust and intelligent workflow. The LLM might:
    -   Add descriptions to each step.
    -   Clean up or combine redundant actions.
    -   Infer the user's intent and add logic.
    -   Define which data should be extracted from a page.
-   **Output**: The builder produces a final, refined `WorkflowDefinitionSchema` (a structured JSON object). This is the executable workflow that the backend will run.

### 3. Execution Phase (`workflow` and `controller` modules)

This is the final phase where the refined workflow is executed.

-   **Mechanism**: The `Workflow` service (`workflow.service.py`) is the main orchestrator. It loads the `WorkflowDefinitionSchema` and executes its steps one by one.
-   **Data Injection**: The `run` method accepts an `inputs` dictionary. These values are loaded into a `context` object. Placeholders in the workflow steps (e.g., a URL or a username in the format `{username}`) are dynamically replaced with values from this context. The output of one step can also be saved to the context for use in a later step.
-   **Step Execution**:
    -   **Deterministic Steps**: For simple, predefined actions like "click" or "input", the `Workflow` service calls the `WorkflowController`. The controller contains the precise code to perform these actions using the browser automation library.
    -   **Agentic Steps**: For complex or ambiguous tasks, the workflow can contain an "agent" step. This delegates control to an LLM-powered agent, which decides on the best course of action to achieve its given task.
-   **LLM-Powered Error Recovery**: A key feature of the execution engine is its ability to recover from errors. If a deterministic step fails (e.g., a button with a specific CSS selector is not found), the system can **fall back to an agent**. It prompts the LLM with the details of the error and the original goal, and the agent attempts to fix the problem and complete the step. This makes the workflows significantly more resilient to minor UI changes.

## File-by-File Breakdown

Here is a detailed description of each file in the `workflows/backend` directory:

### `api.py`

This file is the main entry point for the FastAPI application. Its primary responsibilities are:

-   Initializing the FastAPI app.
-   Configuring Cross-Origin Resource Sharing (CORS) to allow requests from the frontend.
-   Including the API router defined in `routers.py`.
-   Providing an optional standalone runner for starting the server directly.

### `routers.py`

This file defines all the API endpoints for the workflow service. It uses an `APIRouter` to group the workflow-related routes. The key responsibilities include:

-   Defining routes for listing, retrieving, updating, and executing workflows.
-   Handling requests for workflow status, logs, and cancellation.
-   Injecting the `WorkflowService` to handle the business logic for each endpoint.
-   Validating incoming requests and formatting responses using the Pydantic models from `views.py`.

### `service.py`

This file contains the core logic of the workflow backend, encapsulated in the `WorkflowService` class. Its responsibilities include:

-   Managing the lifecycle of workflows, including creation, updates, and deletion.
-   Executing workflows asynchronously in the background using `asyncio`.
-   Tracking the status of active workflow tasks.
-   Handling logging for workflow execution.
-   Interacting with other components, such as the browser controller and LLM instances.

### `views.py`

This file defines the data structures used throughout the API. It contains Pydantic models for:

-   **Request Models**: Defining the expected structure of incoming data for API endpoints (e.g., `WorkflowExecuteRequest`, `WorkflowUpdateRequest`).
-   **Response Models**: Defining the structure of the data returned by the API (e.g., `WorkflowExecuteResponse`, `WorkflowStatusResponse`).
-   **Task Models**: Internal models for tracking the state of workflow tasks (e.g., `TaskInfo`).

Using Pydantic models ensures that the API is well-documented, and that data is validated automatically.
