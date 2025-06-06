import pytest
from rfp_proposal_generator.agents.formatting_agent import FormattingAgent
from rfp_proposal_generator.models.proposal_models import (
    Proposal, ProposalSection, Introduction, ExecutiveSummary,
    TechnicalSolution, TeamQualifications, Pricing
)

@pytest.fixture
def sample_proposal_data():
    intro = Introduction(content="Welcome to this proposal.")
    exec_sum = ExecutiveSummary(content="This proposal will solve all your problems.")
    tech_sol = TechnicalSolution(content="We use cutting-edge tech: A, B, C.")
    team_q = TeamQualifications(content="Our team is composed of experts D, E, F.")
    price = Pricing(content="It will cost $1,000,000.")

    return Proposal(
        rfp_reference_document="ClientRFP-001.pdf",
        target_technology="Quantum Computing",
        introduction=intro,
        executive_summary=exec_sum,
        technical_solution=tech_sol,
        team_qualifications=team_q,
        pricing=price
    )

@pytest.fixture
def minimal_proposal_data():
    return Proposal(
        target_technology="Basic Web Stack",
        technical_solution=TechnicalSolution(content="A simple website using HTML and CSS.")
    )

def test_formatting_agent_instantiation():
    agent = FormattingAgent()
    assert agent is not None

def test_format_full_proposal_to_markdown(sample_proposal_data):
    agent = FormattingAgent()
    markdown = agent.format_proposal_to_markdown(sample_proposal_data)

    assert "**Based on RFP:** ClientRFP-001.pdf" in markdown
    assert "**Proposed Technology Focus:** Quantum Computing" in markdown
    assert "---" in markdown # Separator

    assert "# Introduction" in markdown
    assert "Welcome to this proposal." in markdown

    assert "# Executive Summary" in markdown
    assert "This proposal will solve all your problems." in markdown

    assert "# Technical Solution" in markdown
    assert "We use cutting-edge tech: A, B, C." in markdown

    assert "## Team Qualifications" in markdown # Note: H2
    assert "Our team is composed of experts D, E, F." in markdown

    assert "## Pricing" in markdown # Note: H2
    assert "It will cost $1,000,000." in markdown

    # Check order (simple check)
    intro_pos = markdown.find("# Introduction")
    tech_pos = markdown.find("# Technical Solution")
    team_pos = markdown.find("## Team Qualifications")

    assert 0 < intro_pos < tech_pos < team_pos, "Sections seem to be out of order or missing."

def test_format_minimal_proposal_to_markdown(minimal_proposal_data):
    agent = FormattingAgent()
    markdown = agent.format_proposal_to_markdown(minimal_proposal_data)

    assert "**Proposed Technology Focus:** Basic Web Stack" in markdown
    assert "# Technical Solution" in markdown
    assert "A simple website using HTML and CSS." in markdown

    assert "Introduction" not in markdown # Check that empty sections are not rendered
    assert "Executive Summary" not in markdown
    assert "Team Qualifications" not in markdown
    assert "Pricing" not in markdown

def test_format_proposal_with_empty_section_content():
    agent = FormattingAgent()
    proposal_with_empty_section = Proposal(
        target_technology="Test Tech",
        introduction=Introduction(title="Intro", content="   "), # Empty content
        technical_solution=TechnicalSolution(content="Valid tech solution.")
    )
    markdown = agent.format_proposal_to_markdown(proposal_with_empty_section)

    assert "Intro" not in markdown # Title of empty section should not appear
    assert "# Technical Solution" in markdown
    assert "Valid tech solution." in markdown

def test_format_proposal_no_optional_sections():
    agent = FormattingAgent()
    proposal = Proposal(
        target_technology="Future Tech",
        technical_solution=TechnicalSolution(content="The future is now.")
    )
    markdown = agent.format_proposal_to_markdown(proposal)

    assert "**Proposed Technology Focus:** Future Tech" in markdown
    assert "# Technical Solution" in markdown
    assert "The future is now." in markdown
    assert "Introduction" not in markdown
    assert "Executive Summary" not in markdown
    assert "Team Qualifications" not in markdown
    assert "Pricing" not in markdown
