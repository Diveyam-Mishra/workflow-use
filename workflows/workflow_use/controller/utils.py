import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from browser_use.browser.session import BrowserSession, CDPSession
from browser_use.actor.element import Element
from browser_use.actor.page import Page

logger = logging.getLogger(__name__)


@dataclass
class FrameContext:
	browser_session: BrowserSession
	frame_id: str | None
	frame_info: dict[str, Any] | None
	session: CDPSession

	@property
	def target_id(self) -> str:
		return self.session.target_id

	def create_page(self) -> Page:
		return Page(self.browser_session, self.target_id, session_id=self.session.session_id)


@dataclass
class ElementHandle:
	element: Element
	selector_used: str
	frame_context: FrameContext


def truncate_selector(selector: str, max_length: int = 35) -> str:
	"""Truncate a CSS selector to a maximum length, adding ellipsis if truncated."""
	return selector if len(selector) <= max_length else f'{selector[:max_length]}...'


def _safe_get(params: Any, name: str, default: Any = None) -> Any:
	if params is None:
		return default
	if isinstance(params, dict):
		return params.get(name, default)
	return getattr(params, name, default)


def _parse_frame_path(frame_id_path: str | None) -> List[int]:
	if not frame_id_path or frame_id_path == '0':
		return []
	segments: List[int] = []
	for part in frame_id_path.split('.'):
		part = part.strip()
		if not part:
			continue
		try:
			segments.append(int(part))
		except ValueError:
			logger.debug('Skipping invalid frameIdPath segment: %s', part)
	return segments


def _score_frame_url(frame_url: str | None, target_url: str | None) -> int:
	if not frame_url or not target_url:
		return 0
	try:
		candidate = urlparse(frame_url)
		target = urlparse(target_url)
	except Exception:
		return 0

	score = 0
	if (candidate.scheme, candidate.netloc) == (target.scheme, target.netloc):
		score += 2
		if candidate.path.startswith(target.path):
			score += 1
	if frame_url.startswith(target_url):
		score += 1
	return score


async def _ensure_agent_focus(browser_session: BrowserSession) -> CDPSession:
	if browser_session.agent_focus is None:
		return await browser_session.get_or_create_cdp_session()
	return browser_session.agent_focus


def _find_root_frame(all_frames: dict[str, dict[str, Any]], focus_target_id: str | None) -> Tuple[str | None, dict[str, Any] | None]:
	if not all_frames:
		return None, None
	if focus_target_id:
		for frame_id, info in all_frames.items():
			if info.get('parentFrameId') is None and info.get('frameTargetId') == focus_target_id:
				return frame_id, info
	for frame_id, info in all_frames.items():
		if info.get('parentFrameId') is None:
			return frame_id, info
	# Fallback: first entry
	first_id = next(iter(all_frames.keys()))
	return first_id, all_frames[first_id]


def _follow_frame_path(
	all_frames: dict[str, dict[str, Any]],
	root_id: str | None,
	path_segments: List[int],
) -> Tuple[str | None, dict[str, Any] | None]:
	if root_id is None:
		return None, None
	current_id = root_id
	current_info = all_frames.get(current_id)
	for index in path_segments:
		if not current_info:
			return None, None
		children = current_info.get('childFrameIds') or []
		if 0 <= index < len(children):
			current_id = children[index]
			current_info = all_frames.get(current_id)
		else:
			logger.debug('Frame path index %s out of range for frame %s', index, current_id)
			return None, None
	return current_id, current_info


def _find_best_frame_by_url(
	all_frames: dict[str, dict[str, Any]],
	prefer_url: str | None,
	current_id: str | None,
) -> Tuple[str | None, dict[str, Any] | None]:
	if not prefer_url or not all_frames:
		return current_id, all_frames.get(current_id) if current_id else (None, None)

	best_id = current_id
	best_info = all_frames.get(current_id) if current_id else None
	best_score = _score_frame_url(best_info.get('url') if best_info else None, prefer_url)

	for frame_id, info in all_frames.items():
		score = _score_frame_url(info.get('url'), prefer_url)
		if score > best_score:
			best_id = frame_id
			best_info = info
			best_score = score

	return best_id, best_info


async def _build_frame_context(
	browser_session: BrowserSession,
	frame_id: str | None,
	frame_info: dict[str, Any] | None,
	fallback_session: CDPSession,
) -> FrameContext:
	target_id = frame_info.get('frameTargetId') if frame_info else None
	try:
		if target_id:
			session = await browser_session.get_or_create_cdp_session(target_id, focus=False)
		else:
			session = fallback_session
	except Exception as exc:
		logger.debug('Failed to get CDP session for frame %s (%s), using fallback: %s', frame_id, target_id, exc)
		session = fallback_session

	return FrameContext(
		browser_session=browser_session,
		frame_id=frame_id,
		frame_info=frame_info,
		session=session,
	)


async def _resolve_frame_context(
	browser_session: BrowserSession,
	params: Any,
) -> Tuple[FrameContext, dict[str, dict[str, Any]], dict[str, str]]:
	focus_session = await _ensure_agent_focus(browser_session)

	try:
		all_frames, target_sessions = await browser_session.get_all_frames()
	except Exception as exc:
		logger.debug('Failed to collect frame hierarchy: %s', exc)
		all_frames, target_sessions = {}, {}

	root_id, root_info = _find_root_frame(all_frames, focus_session.target_id if focus_session else None)

	frame_id_path = _safe_get(params, 'frameIdPath')
	segments = _parse_frame_path(frame_id_path)
	if segments:
		selected_id, selected_info = _follow_frame_path(all_frames, root_id, segments)
	else:
		selected_id, selected_info = root_id, root_info

	prefer_url = _safe_get(params, 'frameUrl')
	if prefer_url:
		selected_id, selected_info = _find_best_frame_by_url(all_frames, prefer_url, selected_id)

	if not selected_id and not selected_info:
		selected_id, selected_info = root_id, root_info

	frame_ctx = await _build_frame_context(browser_session, selected_id, selected_info, focus_session)
	return frame_ctx, all_frames, target_sessions


async def _query_selector_in_frame(frame_ctx: FrameContext, selector: str) -> Element | None:
	session = frame_ctx.session
	params: Dict[str, Any] = {'depth': 1}
	if frame_ctx.frame_id:
		params['frameId'] = frame_ctx.frame_id
	try:
		document = await session.cdp_client.send.DOM.getDocument(params=params, session_id=session.session_id)
	except Exception:
		# Fall back to default document retrieval if frame-specific query fails
		document = await session.cdp_client.send.DOM.getDocument(session_id=session.session_id)

	root_node_id = document.get('root', {}).get('nodeId')
	if root_node_id is None:
		return None

	query = await session.cdp_client.send.DOM.querySelector(
		params={'nodeId': root_node_id, 'selector': selector},
		session_id=session.session_id,
	)
	node_id = query.get('nodeId')
	if not node_id:
		return None

	describe = await session.cdp_client.send.DOM.describeNode({'nodeId': node_id}, session_id=session.session_id)
	backend_node_id = describe.get('node', {}).get('backendNodeId')
	if backend_node_id is None:
		return None

	return Element(frame_ctx.browser_session, backend_node_id, session.session_id)


async def _is_element_visible(element: Element) -> bool:
	try:
		bounds = await element.get_bounding_box()
	except Exception:
		return False
	if not bounds:
		return False
	return bounds.width > 0 and bounds.height > 0


async def _wait_for_visible_element(
	frame_ctx: FrameContext,
	selectors: Iterable[str],
	timeout_ms: int,
) -> Tuple[Element, str]:
	selectors_list = list(dict.fromkeys(selectors))
	loop = asyncio.get_running_loop()
	deadline = loop.time() + (timeout_ms / 1000)

	while True:
		remaining = deadline - loop.time()
		if remaining <= 0:
			break

		for selector in selectors_list:
			try:
				element = await _query_selector_in_frame(frame_ctx, selector)
			except Exception as exc:
				logger.debug('Selector %s failed in frame %s: %s', selector, frame_ctx.frame_id, exc)
				continue

			if element and await _is_element_visible(element):
				return element, selector

		await asyncio.sleep(min(0.1, max(remaining / 4, 0.05)))

	raise TimeoutError('Timed out waiting for visible element')


async def _try_selectors_once(
	frame_ctx: FrameContext,
	selectors: Iterable[str],
) -> Tuple[Element, str] | None:
	for selector in selectors:
		try:
			element = await _query_selector_in_frame(frame_ctx, selector)
		except Exception:
			continue
		if element and await _is_element_visible(element):
			return element, selector
	return None


async def _collect_other_frame_contexts(
	browser_session: BrowserSession,
	current_ctx: FrameContext,
	all_frames: dict[str, dict[str, Any]],
	prefer_url: str | None,
) -> List[FrameContext]:
	if not all_frames:
		return []

	seen = set()
	contexts: List[FrameContext] = []
	focus_session = await _ensure_agent_focus(browser_session)

	for frame_id, info in sorted(
		all_frames.items(),
		key=lambda item: _score_frame_url(item[1].get('url'), prefer_url),
		reverse=True,
	):
		if frame_id == current_ctx.frame_id:
			continue
		if frame_id in seen:
			continue
		seen.add(frame_id)
		ctx = await _build_frame_context(browser_session, frame_id, info, focus_session)
		contexts.append(ctx)
	return contexts


async def get_best_element_handle(
	browser_session: BrowserSession,
	selector: str,
	params: Any | None = None,
	timeout_ms: int = 100,
) -> ElementHandle:
	selectors: List[str] = [selector]
	selectors.extend(generate_stable_selectors(selector, params))
	selectors = list(dict.fromkeys(selectors))

	frame_ctx, all_frames, _ = await _resolve_frame_context(browser_session, params)

	try:
		element, selector_used = await _wait_for_visible_element(frame_ctx, selectors, timeout_ms)
		return ElementHandle(element=element, selector_used=selector_used, frame_context=frame_ctx)
	except TimeoutError as exc:
		logger.debug('Primary frame lookup timed out for selector %s: %s', truncate_selector(selector), exc)

	prefer_url = _safe_get(params, 'frameUrl') or _safe_get(params, 'url')

	other_contexts = await _collect_other_frame_contexts(browser_session, frame_ctx, all_frames, prefer_url)
	for ctx in other_contexts:
		result = await _try_selectors_once(ctx, selectors)
		if result:
			element, selector_used = result
			return ElementHandle(element=element, selector_used=selector_used, frame_context=ctx)

	raise Exception(f'Failed to find element. Original selector: {selector}')


def generate_stable_selectors(selector, params=None):
	"""Generate selectors from most to least stable based on selector patterns."""
	fallbacks = []

	# 1. Extract attribute-based selectors (most stable)
	attributes_to_check = [
		'placeholder',
		'aria-label',
		'name',
		'title',
		'role',
		'data-testid',
	]
	for attr in attributes_to_check:
		attr_pattern = rf'\[{attr}\*?=[\'"]([^\'"]*)[\'"]'
		attr_match = re.search(attr_pattern, selector)
		if attr_match:
			attr_value = attr_match.group(1)
			element_tag = extract_element_tag(selector, params)
			if element_tag:
				fallbacks.append(f'{element_tag}[{attr}*="{attr_value}"]')

	# 2. Combine tag + class + one attribute (good stability)
	element_tag = extract_element_tag(selector, params)
	classes = extract_stable_classes(selector)
	for attr in attributes_to_check:
		attr_pattern = rf'\[{attr}\*?=[\'"]([^\'"]*)[\'"]'
		attr_match = re.search(attr_pattern, selector)
		if attr_match and classes and element_tag:
			attr_value = attr_match.group(1)
			class_selector = '.'.join(classes)
			fallbacks.append(f'{element_tag}.{class_selector}[{attr}*="{attr_value}"]')

	# 3. Tag + class combination (less stable but often works)
	if element_tag and classes:
		class_selector = '.'.join(classes)
		fallbacks.append(f'{element_tag}.{class_selector}')

	# 4. Remove dynamic parts (IDs, state classes)
	if '[id=' in selector:
		fallbacks.append(re.sub(r'\[id=[\'"].*?[\'"]\]', '', selector))

	for state in ['.focus-visible', '.hover', '.active', '.focus', ':focus']:
		if state in selector:
			fallbacks.append(selector.replace(state, ''))

	# 5. Use text-based selector if we have element tag and text
	if params and getattr(params, 'elementTag', None) and getattr(params, 'elementText', None) and params.elementText.strip():
		fallbacks.append(f"{params.elementTag}:has-text('{params.elementText}')")

	return list(dict.fromkeys(fallbacks))  # Remove duplicates while preserving order


def extract_element_tag(selector, params=None):
	"""Extract element tag from selector or params."""
	# Try to get from selector first
	tag_match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)', selector)
	if tag_match:
		return tag_match.group(1).lower()

	# Fall back to params
	if params and getattr(params, 'elementTag', None):
		return params.elementTag.lower()

	return ''


def extract_stable_classes(selector):
	"""Extract classes that appear to be stable (not state-related)."""
	class_pattern = r'\.([a-zA-Z0-9_-]+)'
	classes = re.findall(class_pattern, selector)

	# Filter out likely state classes
	stable_classes = [
		cls
		for cls in classes
		if not any(state in cls.lower() for state in ['focus', 'hover', 'active', 'selected', 'checked', 'disabled'])
	]

	return stable_classes


def generate_stable_xpaths(xpath, params=None):
	"""Generate stable XPath alternatives."""
	alternatives = []

	# Handle "id()" XPath pattern which is brittle
	if 'id(' in xpath:
		element_tag = getattr(params, 'elementTag', '').lower()
		if element_tag:
			# Create XPaths based on attributes from params
			if params and getattr(params, 'cssSelector', None):
				for attr in ['placeholder', 'aria-label', 'title', 'name']:
					attr_pattern = rf'\[{attr}\*?=[\'"]([^\'"]*)[\'"]'
					attr_match = re.search(attr_pattern, params.cssSelector)
					if attr_match:
						attr_value = attr_match.group(1)
						alternatives.append(f"//{element_tag}[contains(@{attr}, '{attr_value}')]")

	return alternatives
