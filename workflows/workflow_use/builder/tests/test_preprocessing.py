import pytest
from unittest.mock import MagicMock
from workflow_use.builder.service import BuilderService
from workflow_use.schema.views import Step

# Mock the LLM so we don't need an API key
mock_llm = MagicMock()

# Sample noisy steps data (as Pydantic models)
# In a real scenario, these would be different Step subtypes, but for testing
# the cleaning logic which works on dicts, using the base Step is sufficient.
noisy_steps_data = [
    Step(type='navigation', url='https://www.real-site.com/', timestamp=1000, frameId=0),
    Step(type='navigation', url='about:blank', timestamp=1100, frameId=1),
    Step(type='navigation', url='https://securepubads.g.doubleclick.net/some-ad', timestamp=1200, frameId=1),
    Step(type='navigation', url='https://www.real-site.com/', timestamp=1300, frameId=0), # Redundant
    Step(type='click', xpath='//button[@id="one"]', timestamp=2000, frameId=0),
    Step(type='click', xpath='//button[@id="one"]', timestamp=2020, frameId=0), # Duplicate
    Step(type='click', xpath='//button[@id="one"]', timestamp=2080, frameId=0), # Not a duplicate (time window)
    Step(type='input', xpath='//input', value='test', timestamp=3000, frameId=0),
    Step(type='navigation', url='https://www.another-site.com/', timestamp=4000, frameId=0),
]

@pytest.fixture
def builder_service():
    """Pytest fixture to create a BuilderService instance with a mocked LLM."""
    return BuilderService(llm=mock_llm)

def test_preprocess_and_clean_steps(builder_service):
    """
    Tests the _preprocess_and_clean_steps method to ensure it correctly
    filters and consolidates noisy steps.
    """
    # The method expects a list of Pydantic models, so we pass our sample data
    cleaned_steps_dicts = builder_service._preprocess_and_clean_steps(noisy_steps_data)

    # Expected output after cleaning
    # - about:blank navigation removed
    # - ad domain navigation removed
    # - redundant navigation to real-site.com removed
    # - duplicate click at timestamp 2020 removed
    expected_xpaths = [
        None, # for navigation
        '//button[@id="one"]',
        '//button[@id="one"]',
        '//input',
        None, # for navigation
    ]
    expected_urls = [
        'https://www.real-site.com/',
        None, # for click
        None, # for click
        None, # for input
        'https://www.another-site.com/',
    ]

    # Assertions
    assert len(cleaned_steps_dicts) == 5

    # Check types in order
    expected_types = ['navigation', 'click', 'click', 'input', 'navigation']
    actual_types = [step['type'] for step in cleaned_steps_dicts]
    assert actual_types == expected_types

    # Check that the first click (2000) and the third click (2080) are present
    click_timestamps = [s['timestamp'] for s in cleaned_steps_dicts if s['type'] == 'click']
    assert click_timestamps == [2000, 2080]

    # Check that the ad navigation is gone
    for step in cleaned_steps_dicts:
        if step['type'] == 'navigation':
            assert 'doubleclick.net' not in step['url']
            assert 'about:blank' not in step['url']

    # Check that the first navigation event was kept
    assert cleaned_steps_dicts[0]['type'] == 'navigation'
    assert cleaned_steps_dicts[0]['url'] == 'https://www.real-site.com/'
    assert cleaned_steps_dicts[0]['timestamp'] == 1000

    print("Test passed: `_preprocess_and_clean_steps` correctly filtered and consolidated steps.")
