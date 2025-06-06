import pytest
import os
from unittest.mock import AsyncMock, patch

# Agent being tested
from rfp_proposal_generator.agents.technical_writer_agent import TechnicalWriterAgent, TechnicalContentSet
# Models used by the agent
from rfp_proposal_generator.models.proposal_models import OEMSolutionReview

# Fixture to set OPENAI_API_KEY environment variable for tests
@pytest.fixture(autouse=True)
def set_openai_api_key_for_tech_writer(monkeypatch):
    # The agent's __init__ chain (via AgentBase) checks for this
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_for_pytest_technical_writer")

@pytest.fixture
def sample_rfp_data_for_tech_writer():
    return {
        "rfp_full_text": "Client wants a new e-commerce platform. Key features: product catalog, shopping cart, payment gateway. Must be scalable and secure.",
        "rfp_summary": "Need scalable e-commerce platform with catalog, cart, payments.",
        "key_requirements": ["Product catalog", "Shopping cart", "Payment gateway integration", "Scalability", "Security"],
        "evaluation_criteria": ["Feature set", "Price", "Vendor experience"],
        "chosen_technology": "Python with Django and Stripe"
    }

@pytest.mark.asyncio
async def test_technical_writer_agent_instantiation():
    try:
        agent = TechnicalWriterAgent()
        assert agent is not None
        assert agent.llm_agent is not None, "PydanticAIAgent (self.llm_agent) was not initialized."
    except ValueError as e:
        pytest.fail(f"Agent instantiation failed: {e}")

@pytest.mark.asyncio
async def test_generate_all_technical_content_successful(sample_rfp_data_for_tech_writer):
    agent = TechnicalWriterAgent()

    # This is the Pydantic model instance that PydanticAIAgent.run is expected to return
    # (inside the AgentRunResult.output attribute, but we mock the direct output for simplicity here)
    mock_llm_output = TechnicalContentSet(
        understanding_requirements_content="Understood all requirements clearly.",
        solution_overview_content="The proposed Django solution will be modular and robust.",
        solution_architecture_descriptive_text="Architecture includes web layer, app layer, data layer.",
        solution_architecture_mermaid_script="```mermaid\ngraph TD;\n  WebApp --> AppServer;\n  AppServer --> Database;\n```"
    )

    # Mock the PydanticAIAgent's `run` method which is stored in self.llm_agent
    # The `run` method of `pydantic_ai.Agent` returns an `AgentRunResult` object,
    # and the actual pydantic model is in its `output` attribute.
    mock_agent_run_result = AsyncMock() # Mock for the container object
    mock_agent_run_result.output = mock_llm_output # Set its output attribute

    agent.llm_agent.run = AsyncMock(return_value=mock_agent_run_result)


    result_content_set = await agent.generate_all_technical_content(**sample_rfp_data_for_tech_writer)

    agent.llm_agent.run.assert_called_once()
    call_args = agent.llm_agent.run.call_args
    assert call_args.kwargs['output_type'] == TechnicalContentSet
    assert sample_rfp_data_for_tech_writer['chosen_technology'] in call_args.kwargs['user_prompt']
    assert sample_rfp_data_for_tech_writer['key_requirements'][0] in call_args.kwargs['user_prompt']

    assert isinstance(result_content_set, TechnicalContentSet)
    assert result_content_set.understanding_requirements_content == "Understood all requirements clearly."
    assert "Django solution" in result_content_set.solution_overview_content
    assert "```mermaid" in result_content_set.solution_architecture_mermaid_script

@pytest.mark.asyncio
async def test_generate_all_technical_content_input_validation(sample_rfp_data_for_tech_writer):
    agent = TechnicalWriterAgent()

    invalid_data_no_context = sample_rfp_data_for_tech_writer.copy()
    invalid_data_no_context["rfp_full_text"] = ""
    invalid_data_no_context["rfp_summary"] = None
    invalid_data_no_context["key_requirements"] = []
    with pytest.raises(ValueError, match="Some RFP context .* must be provided"):
        await agent.generate_all_technical_content(**invalid_data_no_context)

    invalid_data_no_tech = sample_rfp_data_for_tech_writer.copy()
    invalid_data_no_tech["chosen_technology"] = ""
    with pytest.raises(ValueError, match="A chosen technology must be specified"):
        await agent.generate_all_technical_content(**invalid_data_no_tech)

@pytest.mark.asyncio
async def test_generate_all_technical_content_llm_exception(sample_rfp_data_for_tech_writer):
    agent = TechnicalWriterAgent()
    # Simulate an error during the LLM call
    agent.llm_agent.run = AsyncMock(side_effect=Exception("LLM API Error"))

    result_content_set = await agent.generate_all_technical_content(**sample_rfp_data_for_tech_writer)

    agent.llm_agent.run.assert_called_once()
    # Check if the fallback error content is present
    assert "Error generating content: LLM API Error" in result_content_set.understanding_requirements_content
    assert "Error generating content: LLM API Error" in result_content_set.solution_overview_content
    assert "Error generating diagram" in result_content_set.solution_architecture_mermaid_script

@pytest.mark.asyncio
async def test_generate_all_technical_content_llm_returns_none(sample_rfp_data_for_tech_writer):
    agent = TechnicalWriterAgent()
    # Simulate LLM returning None or an unexpected structure (no 'output' attribute or None 'output')
    agent.llm_agent.run = AsyncMock(return_value=None) # AgentRunResult is None
    result1 = await agent.generate_all_technical_content(**sample_rfp_data_for_tech_writer)
    assert "Error generating content: Failed to generate technical content due to unexpected LLM response for TechnicalContentSet." in result1.understanding_requirements_content

    agent.llm_agent.run = AsyncMock(return_value=AsyncMock(output=None)) # AgentRunResult.output is None
    result2 = await agent.generate_all_technical_content(**sample_rfp_data_for_tech_writer)
    assert "Error generating content: Failed to generate technical content due to unexpected LLM response for TechnicalContentSet." in result2.understanding_requirements_content


@pytest.mark.asyncio
async def test_generate_oem_review_successful():
    agent = TechnicalWriterAgent()
    oem_product_name = "Salesforce Platform"

    mock_llm_oem_output = OEMSolutionReview(
        oem_product_name=oem_product_name,
        title=f"Overview: {oem_product_name}",
        content="Salesforce is a leading CRM platform..."
    )
    mock_agent_run_result = AsyncMock()
    mock_agent_run_result.output = mock_llm_oem_output
    agent.llm_agent.run = AsyncMock(return_value=mock_agent_run_result)


    result_review = await agent.generate_oem_review(
        oem_product_name=oem_product_name,
        key_requirements=["CRM features", "Cloud hosting"],
        rfp_summary="Client needs a CRM."
    )

    agent.llm_agent.run.assert_called_once()
    call_args = agent.llm_agent.run.call_args
    assert call_args.kwargs['output_type'] == OEMSolutionReview
    assert oem_product_name in call_args.kwargs['user_prompt']

    assert isinstance(result_review, OEMSolutionReview)
    assert result_review.oem_product_name == oem_product_name
    assert result_review.title == f"Overview: {oem_product_name}"
    assert "leading CRM platform" in result_review.content

@pytest.mark.asyncio
async def test_generate_oem_review_input_validation():
    agent = TechnicalWriterAgent()
    with pytest.raises(ValueError, match="OEM product name must be provided"):
        await agent.generate_oem_review("")

@pytest.mark.asyncio
async def test_generate_oem_review_llm_exception():
    agent = TechnicalWriterAgent()
    oem_product_name = "TestPlatform"
    agent.llm_agent.run = AsyncMock(side_effect=Exception("LLM API Error for OEM"))

    result_review = await agent.generate_oem_review(oem_product_name)

    agent.llm_agent.run.assert_called_once()
    assert result_review.oem_product_name == oem_product_name
    assert result_review.title == f"Overview: {oem_product_name}"
    assert "Error generating review" in result_review.content
    assert "LLM API Error for OEM" in result_review.content

@pytest.mark.asyncio
async def test_generate_oem_review_llm_returns_none():
    agent = TechnicalWriterAgent()
    oem_product_name = "TestPlatformNone"

    agent.llm_agent.run = AsyncMock(return_value=None) # AgentRunResult is None
    result1 = await agent.generate_oem_review(oem_product_name)
    assert f"Error generating review for {oem_product_name}: Failed to generate OEM review for {oem_product_name} due to unexpected LLM response." in result1.content

    agent.llm_agent.run = AsyncMock(return_value=AsyncMock(output=None)) # AgentRunResult.output is None
    result2 = await agent.generate_oem_review(oem_product_name)
    assert f"Error generating review for {oem_product_name}: Failed to generate OEM review for {oem_product_name} due to unexpected LLM response." in result2.content
