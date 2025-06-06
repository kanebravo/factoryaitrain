import pytest
import os
from unittest.mock import AsyncMock, patch # AsyncMock for async methods

from rfp_proposal_generator.agents.technical_writer_agent import TechnicalWriterAgent
from rfp_proposal_generator.models.proposal_models import TechnicalSolution

# Fixture to set OPENAI_API_KEY environment variable for tests
@pytest.fixture(autouse=True)
def set_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_for_pytest_technical")

@pytest.fixture
def key_requirements_sample():
    return ["Requirement A: Must do X", "Requirement B: Must integrate with Y"]

@pytest.fixture
def chosen_technology_sample():
    return "Python with FastAPI and PostgreSQL"

@pytest.mark.asyncio
async def test_technical_writer_agent_instantiation():
    try:
        agent = TechnicalWriterAgent()
        assert agent is not None
        assert agent.llm_agent is not None # Check for the pydantic_ai.Agent instance
    except ValueError as e:
        pytest.fail(f"Agent instantiation failed: {e}")

@pytest.mark.asyncio
async def test_generate_technical_solution_successful(key_requirements_sample, chosen_technology_sample):
    agent = TechnicalWriterAgent()

    mock_generated_content = "This is the detailed technical solution using Python with FastAPI..."

    # This is the object that pydantic_ai.Agent.run() is expected to return.
    # It's a container (AgentRunResult) with an 'output' attribute holding the TechnicalSolution.
    mock_run_result_container = AsyncMock()
    mock_run_result_container.output = TechnicalSolution(
        title="Technical Solution", # LLM might generate this, or agent enforces it.
        content=mock_generated_content
    )

    # Mock the pydantic_ai.Agent's `run` method
    # The actual llm_agent is `agent.llm_agent`
    agent.llm_agent.run = AsyncMock(return_value=mock_run_result_container)

    result_solution = await agent.generate_technical_solution(
        key_requirements=key_requirements_sample,
        chosen_technology=chosen_technology_sample,
        rfp_summary="A brief summary of the RFP."
    )

    agent.llm_agent.run.assert_called_once()
    call_args = agent.llm_agent.run.call_args
    assert call_args.kwargs['output_type'] == TechnicalSolution
    assert chosen_technology_sample in call_args.kwargs['user_prompt'] # prompt is passed as user_prompt
    assert key_requirements_sample[0] in call_args.kwargs['user_prompt']

    assert isinstance(result_solution, TechnicalSolution)
    assert result_solution.title == "Technical Solution" # Agent enforces this title
    assert result_solution.content == mock_generated_content

@pytest.mark.asyncio
async def test_generate_technical_solution_input_validation():
    agent = TechnicalWriterAgent()
    with pytest.raises(ValueError, match="Key requirements must be provided"):
        await agent.generate_technical_solution([], "SomeTech")

    with pytest.raises(ValueError, match="A chosen technology must be specified"):
        await agent.generate_technical_solution(["Req 1"], "")

@pytest.mark.asyncio
async def test_generate_technical_solution_llm_exception(key_requirements_sample, chosen_technology_sample):
    agent = TechnicalWriterAgent()

    agent.llm_agent.run = AsyncMock(side_effect=Exception("LLM API Error"))

    expected_error_content = "Error generating content: LLM API Error"
    result_solution = await agent.generate_technical_solution(
        key_requirements=key_requirements_sample,
        chosen_technology=chosen_technology_sample
    )

    agent.llm_agent.run.assert_called_once()
    assert result_solution.title == "Technical Solution"
    assert expected_error_content in result_solution.content

@pytest.mark.asyncio
async def test_generate_technical_solution_llm_returns_none_container(key_requirements_sample, chosen_technology_sample):
    agent = TechnicalWriterAgent()
    agent.llm_agent.run = AsyncMock(return_value=None) # LLM returns None for the container

    result_solution = await agent.generate_technical_solution(
        key_requirements=key_requirements_sample,
        chosen_technology=chosen_technology_sample
    )
    assert result_solution.title == "Technical Solution"
    assert "Error: Failed to generate content due to unexpected LLM response." in result_solution.content

@pytest.mark.asyncio
async def test_generate_technical_solution_llm_returns_container_with_none_output(key_requirements_sample, chosen_technology_sample):
    agent = TechnicalWriterAgent()
    mock_run_result_container = AsyncMock()
    mock_run_result_container.output = None # Output attribute is None
    agent.llm_agent.run = AsyncMock(return_value=mock_run_result_container)

    result_solution = await agent.generate_technical_solution(
        key_requirements=key_requirements_sample,
        chosen_technology=chosen_technology_sample
    )
    assert result_solution.title == "Technical Solution"
    assert "Error: Failed to generate content due to unexpected LLM response." in result_solution.content
