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
