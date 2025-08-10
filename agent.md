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
