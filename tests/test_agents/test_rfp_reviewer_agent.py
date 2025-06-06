import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock # Import AsyncMock
import asyncio

# Import PydanticAgent from where it's defined now (pydantic_ai.agent, but imported as PydanticAgent in rfp_reviewer_agent)
from rfp_proposal_generator.agents.rfp_reviewer_agent import RFPReviewerAgent, RFPReviewResult, PydanticAgent
from rfp_proposal_generator.models.rfp_models import RFP, RFPSection

# Fixture to set OPENAI_API_KEY environment variable for tests
@pytest.fixture(autouse=True)
def set_openai_api_key(monkeypatch):
    # The key itself doesn't matter for these tests as LLM calls are mocked.
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_for_pytest_will_be_mocked_anyway")

@pytest.fixture
def sample_rfp_object():
    return RFP(
        file_name="test.md",
        full_text="This is a test RFP. Requirement 1. Criterion A.",
        sections=[RFPSection(title="Full", content="This is a test RFP. Requirement 1. Criterion A.")]
    )

@pytest.mark.asyncio
async def test_rfp_reviewer_agent_instantiation():
    # Test that agent can be instantiated
    # This also implicitly checks if OPENAI_API_KEY is found by AgentBase
    try:
        agent = RFPReviewerAgent()
        assert agent is not None
        # Check that the PydanticAgent instance is created
        assert agent.structured_llm_agent is not None
        assert agent.model_name == "openai:gpt-3.5-turbo"
    except ValueError as e:
        pytest.fail(f"Agent instantiation failed: {e}")

@pytest.mark.asyncio
async def test_review_rfp_successful_extraction(sample_rfp_object, monkeypatch):
    # This is the object that PydanticAgent's `run` method is expected to return.
    # It's a container-like object (AgentRunResult) which has an 'output' attribute.
    mock_agent_run_result = MagicMock()
    mock_agent_run_result.output = RFPReviewResult(
        summary="Test summary.",
        key_requirements=["Req 1", "Req 2"],
        evaluation_criteria=["Crit A", "Crit B"]
    )

    # We need to mock the PydanticAgent class itself or its 'run' method.
    # When RFPReviewerAgent is instantiated, it creates an instance of PydanticAgent.
    # We want this instance's 'run' method to be a mock.

    # Create an AsyncMock for the PydanticAgent's async 'run' method
    mock_llm_run_method = AsyncMock(return_value=mock_agent_run_result)

    # Mock the PydanticAgent class. When an instance of this mocked class is created,
    # it should have the 'run' method as our AsyncMock.
    mock_pydantic_agent_instance = MagicMock()
    mock_pydantic_agent_instance.run = mock_llm_run_method

    monkeypatch.setattr(
        "rfp_proposal_generator.agents.rfp_reviewer_agent.PydanticAgent",
        MagicMock(return_value=mock_pydantic_agent_instance) # Return our instance with the async mock run method
    )

    agent = RFPReviewerAgent() # This will now use the mocked PydanticAgent

    updated_rfp = await agent.review_rfp(sample_rfp_object)

    mock_llm_run_method.assert_called_once()
    args, kwargs = mock_llm_run_method.call_args

    # The prompt is passed as user_prompt to pydantic_ai.Agent.run()
    assert "RFP Text:" in kwargs['user_prompt']
    assert "This is a test RFP." in kwargs['user_prompt']

    assert updated_rfp.summary == "Test summary."
    assert updated_rfp.key_requirements == ["Req 1", "Req 2"]
    assert updated_rfp.evaluation_criteria == ["Crit A", "Crit B"]

@pytest.mark.asyncio
async def test_review_rfp_empty_full_text(sample_rfp_object):
    agent = RFPReviewerAgent() # Real agent, no mocking needed here as it's pre-LLM call logic
    sample_rfp_object.full_text = ""

    with pytest.raises(ValueError, match="RFP document full_text is empty. Cannot review."):
        await agent.review_rfp(sample_rfp_object)

@pytest.mark.asyncio
async def test_review_rfp_llm_exception(sample_rfp_object, monkeypatch):
    mock_llm_run_method = AsyncMock(side_effect=Exception("LLM API Error"))

    mock_pydantic_agent_instance = MagicMock()
    mock_pydantic_agent_instance.run = mock_llm_run_method

    monkeypatch.setattr(
        "rfp_proposal_generator.agents.rfp_reviewer_agent.PydanticAgent",
        MagicMock(return_value=mock_pydantic_agent_instance)
    )

    agent = RFPReviewerAgent()

    original_summary = sample_rfp_object.summary
    original_key_requirements = sample_rfp_object.key_requirements
    original_evaluation_criteria = sample_rfp_object.evaluation_criteria

    # The agent currently catches the exception, prints it, and returns the rfp_document without updates.
    updated_rfp = await agent.review_rfp(sample_rfp_object)

    mock_llm_run_method.assert_called_once()
    assert updated_rfp.summary == original_summary
    assert updated_rfp.key_requirements == original_key_requirements
    assert updated_rfp.evaluation_criteria == original_evaluation_criteria

@pytest.mark.asyncio
async def test_review_rfp_llm_returns_none(sample_rfp_object, monkeypatch):
    # Test case where LLM might return None or an object without 'output'
    mock_llm_run_method = AsyncMock(return_value=None) # Simulate LLM returning None

    mock_pydantic_agent_instance = MagicMock()
    mock_pydantic_agent_instance.run = mock_llm_run_method

    monkeypatch.setattr(
        "rfp_proposal_generator.agents.rfp_reviewer_agent.PydanticAgent",
        MagicMock(return_value=mock_pydantic_agent_instance)
    )

    agent = RFPReviewerAgent()
    updated_rfp = await agent.review_rfp(sample_rfp_object)

    mock_llm_run_method.assert_called_once()
    assert updated_rfp.summary is None # Or whatever the initial state was
    assert updated_rfp.key_requirements is None
    assert updated_rfp.evaluation_criteria is None

@pytest.mark.asyncio
async def test_review_rfp_llm_returns_object_without_output_attr(sample_rfp_object, monkeypatch):
    mock_agent_run_result = MagicMock()
    # Simulate the returned container not having the 'output' attribute
    if hasattr(mock_agent_run_result, 'output'): # Ensure it exists before deleting
        del mock_agent_run_result.output

    mock_llm_run_method = AsyncMock(return_value=mock_agent_run_result)

    mock_pydantic_agent_instance = MagicMock()
    mock_pydantic_agent_instance.run = mock_llm_run_method

    monkeypatch.setattr(
        "rfp_proposal_generator.agents.rfp_reviewer_agent.PydanticAgent",
        MagicMock(return_value=mock_pydantic_agent_instance)
    )

    agent = RFPReviewerAgent()
    updated_rfp = await agent.review_rfp(sample_rfp_object)

    mock_llm_run_method.assert_called_once()
    assert updated_rfp.summary is None
    assert updated_rfp.key_requirements is None
    assert updated_rfp.evaluation_criteria is None
