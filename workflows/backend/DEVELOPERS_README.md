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
