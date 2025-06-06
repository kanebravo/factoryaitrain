import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch

from rfp_proposal_generator.generator import ProposalGenerator
from rfp_proposal_generator.models.rfp_models import RFP, RFPSection
from rfp_proposal_generator.models.proposal_models import Proposal, TechnicalSolution, Introduction, ExecutiveSummary

# Fixture to set OPENAI_API_KEY environment variable for tests
@pytest.fixture(autouse=True)
def set_openai_api_key_for_generator(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_for_generator_tests")

@pytest.fixture
def mock_rfp_parser_instance(): # Renamed to clarify it's an instance
    parser_mock = MagicMock()
    parsed_rfp = RFP(
        file_name="test_rfp.md",
        full_text="Full RFP text content.",
        sections=[RFPSection(title="Full", content="Full RFP text content.")],
        summary=None,
        key_requirements=None,
        evaluation_criteria=None
    )
    parser_mock.parse.return_value = parsed_rfp
    return parser_mock

@pytest.fixture
def mock_rfp_reviewer_agent_instance(): # Renamed
    agent_mock = AsyncMock()
    def side_effect_review_rfp(rfp_doc):
        rfp_doc.summary = "AI Generated Summary"
        rfp_doc.key_requirements = ["AI Req 1", "AI Req 2"]
        rfp_doc.evaluation_criteria = ["AI Eval A", "AI Eval B"]
        return rfp_doc
    # Configure the mock instance's method
    agent_mock.review_rfp = AsyncMock(side_effect=side_effect_review_rfp)
    return agent_mock


@pytest.fixture
def mock_technical_writer_agent_instance(): # Renamed
    agent_mock = AsyncMock()
    generated_solution = TechnicalSolution(
        title="Technical Solution",
        content="AI generated technical solution content."
    )
    agent_mock.generate_technical_solution = AsyncMock(return_value=generated_solution)
    return agent_mock

@pytest.fixture
def mock_formatting_agent_instance(): # Renamed
    agent_mock = MagicMock()
    agent_mock.format_proposal_to_markdown.return_value = "# Mocked Markdown Proposal"
    return agent_mock


@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
@patch('rfp_proposal_generator.generator.TechnicalWriterAgent')
@patch('rfp_proposal_generator.generator.FormattingAgent')
async def test_proposal_generator_flow(
    MockFormattingAgent, MockTechnicalWriterAgent, MockRFPReviewerAgent, MockRFPParser,
    mock_rfp_parser_instance, mock_rfp_reviewer_agent_instance,
    mock_technical_writer_agent_instance, mock_formatting_agent_instance
):
    # When these classes are constructed inside ProposalGenerator, they will return our mock instances.
    MockRFPParser.return_value = mock_rfp_parser_instance
    MockRFPReviewerAgent.return_value = mock_rfp_reviewer_agent_instance
    MockTechnicalWriterAgent.return_value = mock_technical_writer_agent_instance
    MockFormattingAgent.return_value = mock_formatting_agent_instance

    generator = ProposalGenerator()

    rfp_file_path = "dummy_rfp.md"
    target_technology = "TestTech"

    # Mock os.path.exists used by RFPParser.__init__
    # This ensures RFPParser(file_path=rfp_file_path) doesn't raise FileNotFoundError
    with patch('os.path.exists', return_value=True):
        markdown_output = await generator.generate_proposal(rfp_file_path, target_technology)

    # Assertions
    # Check that the __init__ of RFPParser was called with the correct path by the generator
    MockRFPParser.assert_called_once_with(file_path=rfp_file_path)
    mock_rfp_parser_instance.parse.assert_called_once()

    mock_rfp_reviewer_agent_instance.review_rfp.assert_called_once()
    # The actual RFP object from parser_mock.parse() should be passed
    rfp_arg_to_reviewer = mock_rfp_reviewer_agent_instance.review_rfp.call_args[0][0]
    assert rfp_arg_to_reviewer.full_text == "Full RFP text content."

    mock_technical_writer_agent_instance.generate_technical_solution.assert_called_once_with(
        key_requirements=["AI Req 1", "AI Req 2"],
        chosen_technology=target_technology,
        rfp_summary="AI Generated Summary"
    )

    mock_formatting_agent_instance.format_proposal_to_markdown.assert_called_once()
    final_proposal_arg = mock_formatting_agent_instance.format_proposal_to_markdown.call_args[0][0]
    assert isinstance(final_proposal_arg, Proposal)
    assert final_proposal_arg.target_technology == target_technology
    assert final_proposal_arg.technical_solution.content == "AI generated technical solution content."
    assert "AI Generated Summary" in final_proposal_arg.executive_summary.content
    assert "solution for the project described in test_rfp.md" in final_proposal_arg.introduction.content

    assert markdown_output == "# Mocked Markdown Proposal"


@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent') # Still need to mock this as it's instantiated
async def test_proposal_generator_empty_rfp_parse(MockRFPReviewerAgent, MockRFPParser):
    empty_parsed_rfp = RFP(file_name="empty.md", full_text="  ", sections=[])
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse.return_value = empty_parsed_rfp
    MockRFPParser.return_value = mock_parser_instance # This is what RFPParser() will return

    # Mock the agent that would be called after parser
    MockRFPReviewerAgent.return_value = AsyncMock()

    generator = ProposalGenerator()
    with patch('os.path.exists', return_value=True): # Ensure RFPParser.__init__ doesn't fail
        with pytest.raises(ValueError, match="Failed to parse content from RFP file: empty.md"):
            await generator.generate_proposal("empty.md", "SomeTech")


@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
@patch('rfp_proposal_generator.generator.TechnicalWriterAgent') # Still need to mock this
async def test_proposal_generator_no_requirements_from_review(
    MockTechnicalWriterAgent, MockRFPReviewerAgent, MockRFPParser,
    mock_rfp_parser_instance # Use fixture that returns RFP with full_text
):
    MockRFPParser.return_value = mock_rfp_parser_instance

    mock_reviewer_instance = AsyncMock()
    def side_effect_no_reqs(rfp_doc):
        rfp_doc.summary = "Summary exists"
        rfp_doc.key_requirements = [] # Empty list of requirements
        rfp_doc.evaluation_criteria = ["Eval criteria exist"]
        return rfp_doc
    mock_reviewer_instance.review_rfp = AsyncMock(side_effect=side_effect_no_reqs)
    MockRFPReviewerAgent.return_value = mock_reviewer_instance

    MockTechnicalWriterAgent.return_value = AsyncMock()

    generator = ProposalGenerator()
    with patch('os.path.exists', return_value=True): # Ensure RFPParser.__init__ doesn't fail
        with pytest.raises(ValueError, match="Cannot generate technical solution without key requirements from RFP review."):
            await generator.generate_proposal("dummy_rfp.md", "SomeTech")
