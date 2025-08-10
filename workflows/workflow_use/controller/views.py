from typing import Literal, Optional

from pydantic import BaseModel


# Shared config allowing extra fields so recorder payloads pass through
class _BaseExtra(BaseModel):
	"""Base model ignoring unknown fields."""

	class Config:
		extra = 'ignore'


# Mixin for shared step metadata (timestamp and tab context)
class StepMeta(_BaseExtra):
	timestamp: int
	tabId: int


# Common optional fields present in recorder events
class RecorderBase(StepMeta):
	xpath: Optional[str] = None
	elementTag: Optional[str] = None
	elementText: Optional[str] = None
	frameUrl: Optional[str] = None
	screenshot: Optional[str] = None


class ClickElementDeterministicAction(RecorderBase):
	"""Parameters for clicking an element identified by CSS selector."""

	type: Literal['click']
	cssSelector: str


class InputTextDeterministicAction(RecorderBase):
	"""Parameters for entering text into an input field identified by CSS selector."""

	type: Literal['input']
	cssSelector: str
	value: str


class SelectDropdownOptionDeterministicAction(RecorderBase):
	"""Parameters for selecting a dropdown option identified by *selector* and *text*."""

	type: Literal['select_change']
	cssSelector: str
	selectedValue: str
	selectedText: str


class KeyPressDeterministicAction(RecorderBase):
	"""Parameters for pressing a key on an element identified by CSS selector."""

	type: Literal['key_press']
	cssSelector: str
	key: str


class NavigationAction(_BaseExtra):
	"""Parameters for navigating to a URL."""

	type: Literal['navigation']
	url: str


class ScrollDeterministicAction(_BaseExtra):
	"""Parameters for scrolling the page by x/y offsets (pixels)."""

	type: Literal['scroll']
	scrollX: int = 0
	scrollY: int = 0
	targetId: Optional[int] = None


class PageExtractionAction(_BaseExtra):
	"""Parameters for extracting content from the page."""

	type: Literal['extract_page_content']
	goal: str


# ---------------- Assertion Actions (new) ----------------

class AssertElementExistsAction(_BaseExtra):
	"""Assert that an element located by a CSS selector exists on the current page."""

	type: Literal['assert_element_exists']
	cssSelector: str
	timeoutMs: Optional[int] = 2000


class AssertTextContainsAction(_BaseExtra):
	"""Assert that the page (or a specific element) contains the expected text substring."""

	type: Literal['assert_text_contains']
	expected: str
	cssSelector: Optional[str] = None  # If provided, scope the text search to this element
	timeoutMs: Optional[int] = 2000


class AssertUrlContainsAction(_BaseExtra):
	"""Assert that the current page URL contains a given substring."""

	type: Literal['assert_url_contains']
	expected: str
