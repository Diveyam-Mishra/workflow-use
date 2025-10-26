import asyncio
import logging

from browser_use import Browser
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Controller
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from workflow_use.controller.utils import ElementHandle, get_best_element_handle, truncate_selector
from workflow_use.controller.views import (
	ClickElementDeterministicAction,
	InputTextDeterministicAction,
	KeyPressDeterministicAction,
	NavigationAction,
	PageExtractionAction,
	ScrollDeterministicAction,
	SelectDropdownOptionDeterministicAction,
)

logger = logging.getLogger(__name__)

DEFAULT_ACTION_TIMEOUT_MS = 2500

# List of default actions from browser_use.controller.service.Controller to disable
# todo: come up with a better way to filter out the actions (filter IN the actions would be much nicer in this case)
DISABLED_DEFAULT_ACTIONS = [
	'done',
	'search_google',
	'go_to_url',
	'go_back',
	'wait',
	'click_element_by_index',
	'input_text',
	'save_pdf',
	'switch_tab',
	'open_tab',
	'close_tab',
	'extract_content',
	'scroll_down',
	'scroll_up',
	'send_keys',
	'scroll_to_text',
	'get_dropdown_options',
	'select_dropdown_option',
	'drag_drop',
	'get_sheet_contents',
	'select_cell_or_range',
	'get_range_contents',
	'clear_selected_range',
	'input_selected_cell_text',
	'update_range_contents',
]


class WorkflowController(Controller):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, exclude_actions=DISABLED_DEFAULT_ACTIONS, **kwargs)
		self.__register_actions()

	def __register_actions(self):
		# Navigate to URL ------------------------------------------------------------
		@self.registry.action('Manually navigate to URL', param_model=NavigationAction)
		async def navigation(params: NavigationAction, browser_session: Browser) -> ActionResult:
			await browser_session.navigate_to(params.url)
			msg = f'Navigated to URL: {params.url}'
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Click element by CSS selector --------------------------------------------------

		@self.registry.action(
			'Click element by all available selectors',
			param_model=ClickElementDeterministicAction,
		)
		async def click(params: ClickElementDeterministicAction, browser_session: Browser) -> ActionResult:
			original_selector = params.cssSelector

			page = await browser_session.must_get_current_page()
			current_url = (await page.get_url() or '').split('#')[0]
			declared_url = (getattr(params, 'url', None) or '').split('#')[0]
			has_frame_hints = bool(getattr(params, 'frameIdPath', None) or getattr(params, 'frameUrl', None))

			if declared_url and declared_url.startswith('http') and not has_frame_hints and declared_url != current_url:
				await browser_session.navigate_to(declared_url)

			handle: ElementHandle = await get_best_element_handle(
				browser_session,
				params.cssSelector,
				params,
				timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
			)

			await handle.element.click()

			msg = (
				f'Clicked element with CSS selector: {truncate_selector(handle.selector_used)} '
				f'(original: {truncate_selector(original_selector)})'
			)
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Input text into element --------------------------------------------------------
		@self.registry.action(
			'Input text into an element by all available selectors',
			param_model=InputTextDeterministicAction,
		)
		async def input(
			params: InputTextDeterministicAction,
			browser_session: Browser,
			has_sensitive_data: bool = False,
		) -> ActionResult:
			original_selector = params.cssSelector

			handle: ElementHandle = await get_best_element_handle(
				browser_session,
				params.cssSelector,
				params,
				timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
			)

			await handle.element.fill(params.value)
			# Allow UI time to reflect the change and avoid flakiness
			await asyncio.sleep(0.2)

			msg = (
				f'Input "{params.value}" into element with CSS selector: {truncate_selector(handle.selector_used)} '
				f'(original: {truncate_selector(original_selector)})'
			)
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Select dropdown option ---------------------------------------------------------
		@self.registry.action(
			'Select dropdown option by all available selectors and visible text',
			param_model=SelectDropdownOptionDeterministicAction,
		)
		async def select_change(params: SelectDropdownOptionDeterministicAction, browser_session: Browser) -> ActionResult:
			original_selector = params.cssSelector

			handle: ElementHandle = await get_best_element_handle(
				browser_session,
				params.cssSelector,
				params,
				timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
			)

			await handle.element.select_option(label=params.selectedText)

			msg = (
				f'Selected option "{params.selectedText}" in dropdown {truncate_selector(handle.selector_used)} '
				f'(original: {truncate_selector(original_selector)})'
			)
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Key press action ------------------------------------------------------------
		@self.registry.action(
			'Press key on element by all available selectors',
			param_model=KeyPressDeterministicAction,
		)
		async def key_press(params: KeyPressDeterministicAction, browser_session: Browser) -> ActionResult:
			original_selector = params.cssSelector

			handle: ElementHandle = await get_best_element_handle(
				browser_session,
				params.cssSelector,
				params,
				timeout_ms=5000,
			)

			await handle.element.focus()
			page = handle.frame_context.create_page()
			await page.press(params.key)

			msg = (
				f"Pressed key '{params.key}' on element with CSS selector: "
				f'{truncate_selector(handle.selector_used)} (original: {truncate_selector(original_selector)})'
			)
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Scroll action --------------------------------------------------------------
		@self.registry.action('Scroll page', param_model=ScrollDeterministicAction)
		async def scroll(params: ScrollDeterministicAction, browser_session: Browser) -> ActionResult:
			page = await browser_session.must_get_current_page()
			await page.evaluate('(x, y) => { window.scrollBy(x, y); return ""; }', params.scrollX, params.scrollY)
			msg = f'Scrolled page by (x={params.scrollX}, y={params.scrollY})'
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Extract content ------------------------------------------------------------
		@self.registry.action(
			'Extract page content to retrieve specific information from the page, e.g. all company names, a specific description, all information about, links with companies in structured format or simply links',
			param_model=PageExtractionAction,
		)
		async def extract_page_content(
			params: PageExtractionAction, browser_session: Browser, page_extraction_llm: BaseChatModel
		):
			page = await browser_session.must_get_current_page()
			import markdownify

			try:
				html = await page.evaluate('() => document.documentElement.outerHTML')
			except Exception as exc:
				logger.debug('Failed to capture page HTML via evaluate: %s', exc)
				html = ''

			content = markdownify.markdownify(html, strip=['a', 'img']) if html else ''


			prompt = (
				'Your task is to extract the content of the page. You will be given a page and a goal and you should '
				'extract all relevant information around this goal from the page. If the goal is vague, summarize the '
				'page. Respond in json format. Extraction goal: {goal}, Page: {page}'
			)
			template = PromptTemplate(input_variables=['goal', 'page'], template=prompt)
			try:
				output = await page_extraction_llm.ainvoke(template.format(goal=params.goal, page=content))
				msg = f'Extracted from page: {output.content}'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				logger.debug('Error extracting content with LLM: %s', e)
				msg = f'Extracted from page: {content}'
				logger.info(msg)
				return ActionResult(extracted_content=msg)
