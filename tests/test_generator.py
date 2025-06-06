import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Component being tested
from rfp_proposal_generator.generator import ProposalGenerator
# Models used in type hinting and constructing test data
from rfp_proposal_generator.models.rfp_models import RFP, RFPSection
from rfp_proposal_generator.models.proposal_models import (
    Proposal, UnderstandingRequirements, SolutionOverview,
    SolutionArchitecture, OEMSolutionReview
)
# For mocking TechnicalWriterAgent's output
from rfp_proposal_generator.agents.technical_writer_agent import TechnicalContentSet


# Fixture to set OPENAI_API_KEY environment variable for all generator tests
@pytest.fixture(autouse=True)
def set_openai_api_key_for_generator(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_for_generator_tests")

# Mock for RFPParser
@pytest.fixture
def mock_rfp_parser_revised():
    parser_mock = MagicMock()
    # RFPParser's parse() method returns an RFP model instance
    parsed_rfp = RFP(
        file_name="test_rfp.md",
        full_text="Full RFP text for context.",
        sections=[RFPSection(title="Full", content="Full RFP text for context.")]
        # summary, key_requirements, etc., are added by RFPReviewerAgent
    )
    parser_mock.parse.return_value = parsed_rfp
    return parser_mock

# Mock for RFPReviewerAgent
@pytest.fixture
def mock_rfp_reviewer_agent_revised():
    agent_mock = AsyncMock()
    # review_rfp method modifies and returns the RFP object
    def side_effect_review_rfp(rfp_doc: RFP) -> RFP: # Type hint for clarity
        rfp_doc.summary = "AI Generated Summary from Reviewer"
        rfp_doc.key_requirements = ["AI Req 1 from Reviewer", "AI Req 2 from Reviewer"]
        rfp_doc.evaluation_criteria = ["AI Eval A from Reviewer", "AI Eval B from Reviewer"]
        return rfp_doc
    agent_mock.review_rfp = AsyncMock(side_effect=side_effect_review_rfp) # Use AsyncMock for the method
    return agent_mock

# Mock for TechnicalWriterAgent
@pytest.fixture
def mock_technical_writer_agent_revised():
    agent_mock = AsyncMock()
    # Mock for generate_all_technical_content
    generated_tech_set = TechnicalContentSet(
        understanding_requirements_content="Detailed understanding of requirements.",
        solution_overview_content="Comprehensive solution overview.",
        solution_architecture_descriptive_text="Scalable architecture description.",
        solution_architecture_mermaid_script="```mermaid\ngraph TD;\n  X-->Y;\n```"
    )
    agent_mock.generate_all_technical_content = AsyncMock(return_value=generated_tech_set) # Use AsyncMock

    # Mock for generate_oem_review
    generated_oem_review = OEMSolutionReview(
        oem_product_name="MockedOEM", # Will be set by call arg usually
        title="Overview: MockedOEM",
        content="This is a great OEM product."
    )
    agent_mock.generate_oem_review = AsyncMock(return_value=generated_oem_review) # Use AsyncMock
    return agent_mock

# Mock for FormattingAgent
@pytest.fixture
def mock_formatting_agent_revised():
    agent_mock = MagicMock()
    agent_mock.format_proposal_to_markdown.return_value = "# Mocked Markdown Output - Revised"
    return agent_mock

# Patch paths are relative to where 'ProposalGenerator' is defined (rfp_proposal_generator.generator)
@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
@patch('rfp_proposal_generator.generator.TechnicalWriterAgent')
@patch('rfp_proposal_generator.generator.FormattingAgent')
async def test_proposal_generator_flow_revised_no_oem(
    MockFormattingAgent, MockTechnicalWriterAgent, MockRFPReviewerAgent, MockRFPParser, # Patched classes
    mock_formatting_agent_revised, mock_technical_writer_agent_revised, # Mock instances
    mock_rfp_reviewer_agent_revised, mock_rfp_parser_revised
):
    # Setup return values for the patched class constructors
    MockRFPParser.return_value = mock_rfp_parser_revised
    MockRFPReviewerAgent.return_value = mock_rfp_reviewer_agent_revised
    MockTechnicalWriterAgent.return_value = mock_technical_writer_agent_revised
    MockFormattingAgent.return_value = mock_formatting_agent_revised

    generator = ProposalGenerator() # API key is set by autouse fixture

    rfp_file_path = "dummy_rfp_non_oem.md"
    target_technology = "GenericCustomTech"

    # Mock _is_oem_technology to ensure it returns False for this test
    # generator._is_oem_technology = MagicMock(return_value=False) # Not needed if we don't want to test _is_oem_technology itself
                                                                # We can just test by providing a non-OEM name

    # Patch os.path.exists used by RFPParser.__init__
    with patch('os.path.exists', return_value=True):
        markdown_output = await generator.generate_proposal(rfp_file_path, target_technology)

    # Assertions on mocks
    MockRFPParser.assert_called_once_with(file_path=rfp_file_path)
    mock_rfp_parser_revised.parse.assert_called_once()
    mock_rfp_reviewer_agent_revised.review_rfp.assert_called_once()

    mock_technical_writer_agent_revised.generate_all_technical_content.assert_called_once_with(
        rfp_full_text="Full RFP text for context.",
        rfp_summary="AI Generated Summary from Reviewer",
        key_requirements=["AI Req 1 from Reviewer", "AI Req 2 from Reviewer"],
        evaluation_criteria=["AI Eval A from Reviewer", "AI Eval B from Reviewer"],
        chosen_technology=target_technology
    )
    mock_technical_writer_agent_revised.generate_oem_review.assert_not_called()

    mock_formatting_agent_revised.format_proposal_to_markdown.assert_called_once()
    final_proposal_arg = mock_formatting_agent_revised.format_proposal_to_markdown.call_args[0][0]

    assert isinstance(final_proposal_arg, Proposal)
    assert final_proposal_arg.target_technology == target_technology
    assert final_proposal_arg.understanding_requirements.content == "Detailed understanding of requirements."
    assert final_proposal_arg.solution_overview.content == "Comprehensive solution overview."
    assert final_proposal_arg.solution_architecture.descriptive_text == "Scalable architecture description."
    assert "X-->Y" in final_proposal_arg.solution_architecture.mermaid_script
    assert final_proposal_arg.oem_solution_reviews is None

    assert markdown_output == "# Mocked Markdown Output - Revised"

@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
@patch('rfp_proposal_generator.generator.TechnicalWriterAgent')
@patch('rfp_proposal_generator.generator.FormattingAgent')
async def test_proposal_generator_flow_revised_with_oem(
    MockFormattingAgent, MockTechnicalWriterAgent, MockRFPReviewerAgent, MockRFPParser,
    mock_formatting_agent_revised, mock_technical_writer_agent_revised,
    mock_rfp_reviewer_agent_revised, mock_rfp_parser_revised
):
    MockRFPParser.return_value = mock_rfp_parser_revised
    MockRFPReviewerAgent.return_value = mock_rfp_reviewer_agent_revised
    MockTechnicalWriterAgent.return_value = mock_technical_writer_agent_revised
    MockFormattingAgent.return_value = mock_formatting_agent_revised

    generator = ProposalGenerator()
    rfp_file_path = "dummy_rfp_oem.md"
    target_technology_oem = "OutSystems"

    # No need to mock _is_oem_technology if we rely on its actual implementation
    # generator._is_oem_technology = MagicMock(return_value=True)

    # Ensure the mock OEM review has the correct product name that would be passed
    mock_technical_writer_agent_revised.generate_oem_review.return_value = OEMSolutionReview(
        oem_product_name=target_technology_oem,
        title=f"Overview: {target_technology_oem}",
        content="Specific review for OutSystems."
    )

    with patch('os.path.exists', return_value=True):
        markdown_output = await generator.generate_proposal(rfp_file_path, target_technology_oem)

    mock_technical_writer_agent_revised.generate_all_technical_content.assert_called_once()
    mock_technical_writer_agent_revised.generate_oem_review.assert_called_once_with(
        oem_product_name=target_technology_oem,
        key_requirements=["AI Req 1 from Reviewer", "AI Req 2 from Reviewer"],
        rfp_summary="AI Generated Summary from Reviewer"
    )

    mock_formatting_agent_revised.format_proposal_to_markdown.assert_called_once()
    final_proposal_arg = mock_formatting_agent_revised.format_proposal_to_markdown.call_args[0][0]

    assert isinstance(final_proposal_arg.oem_solution_reviews, list)
    assert len(final_proposal_arg.oem_solution_reviews) == 1
    assert final_proposal_arg.oem_solution_reviews[0].oem_product_name == target_technology_oem
    assert "Specific review for OutSystems." in final_proposal_arg.oem_solution_reviews[0].content

    assert markdown_output == "# Mocked Markdown Output - Revised"


@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
async def test_proposal_generator_empty_rfp_parse_revised(MockRFPReviewerAgent, MockRFPParser):
    empty_parsed_rfp = RFP(file_name="empty.md", full_text="  ", sections=[])
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse.return_value = empty_parsed_rfp
    MockRFPParser.return_value = mock_parser_instance
    MockRFPReviewerAgent.return_value = AsyncMock()

    generator = ProposalGenerator()
    with patch('os.path.exists', return_value=True):
        with pytest.raises(ValueError, match="Failed to parse content from RFP file: empty.md"):
            await generator.generate_proposal("empty.md", "SomeTech")

@pytest.mark.asyncio
@patch('rfp_proposal_generator.generator.RFPParser')
@patch('rfp_proposal_generator.generator.RFPReviewerAgent')
@patch('rfp_proposal_generator.generator.TechnicalWriterAgent')
async def test_proposal_generator_no_requirements_from_review_revised(
    MockTechnicalWriterAgent, MockRFPReviewerAgent, MockRFPParser,
    mock_rfp_parser_revised
):
    MockRFPParser.return_value = mock_rfp_parser_revised

    mock_reviewer_instance = AsyncMock()
    def side_effect_no_reqs(rfp_doc):
        rfp_doc.summary = "Summary exists"
        rfp_doc.key_requirements = []
        rfp_doc.evaluation_criteria = ["Eval criteria exist"]
        return rfp_doc
    mock_reviewer_instance.review_rfp = AsyncMock(side_effect=side_effect_no_reqs)
    MockRFPReviewerAgent.return_value = mock_reviewer_instance

    mock_tech_writer_instance = AsyncMock()
    mock_tech_writer_instance.generate_all_technical_content.return_value = TechnicalContentSet(
        understanding_requirements_content="Generated understanding with no specific reqs.",
        solution_overview_content="Generated overview.",
        solution_architecture_descriptive_text="Generated arch text.",
        solution_architecture_mermaid_script="```mermaid\ngraph TD;\n  None;\n```"
    )
    MockTechnicalWriterAgent.return_value = mock_tech_writer_instance

    generator = ProposalGenerator()
    with patch('os.path.exists', return_value=True):
      await generator.generate_proposal("dummy_rfp.md", "SomeTech")

    mock_tech_writer_instance.generate_all_technical_content.assert_called_once()
    call_args_list = mock_tech_writer_instance.generate_all_technical_content.call_args_list
    assert len(call_args_list) == 1
    call_kwargs = call_args_list[0].kwargs
    assert call_kwargs['key_requirements'] == []
