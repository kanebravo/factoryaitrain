import pytest
from rfp_proposal_generator.agents.formatting_agent import FormattingAgent
from rfp_proposal_generator.models.proposal_models import (
    Proposal, UnderstandingRequirements, SolutionOverview,
    SolutionArchitecture, OEMSolutionReview
)

@pytest.fixture
def sample_technical_proposal_data():
    understanding = UnderstandingRequirements(
        title="Understanding of Requirements", # Title is default, but can be overridden by agent
        content="The client requires a robust e-commerce platform with specific features A, B, and C. The primary goal is to increase sales by 30%."
    )
    overview = SolutionOverview(
        title="Solution Overview",
        content="We propose a cloud-native microservices architecture utilizing Python and React. This will ensure scalability and maintainability."
    )
    architecture = SolutionArchitecture(
        title="Solution Architecture", # Default title
        descriptive_text="The system will have a presentation layer, an application layer with microservices, and a data persistence layer. See diagram below.",
        mermaid_script="```mermaid\ngraph TD;\n  User --> Frontend;\n  Frontend --> Backend_API;\n  Backend_API --> Service_A;\n  Backend_API --> Service_B;\n  Service_A --> Database;\n  Service_B --> Database;\n```"
    )
    oem_review = OEMSolutionReview(
        oem_product_name="AmazingCache",
        title="Overview: AmazingCache", # Title set by agent
        content="AmazingCache is a distributed caching solution that will enhance performance."
    )
    return Proposal(
        rfp_reference_document="ClientRFP-Tech-002.pdf",
        target_technology="Python, React, Microservices & AmazingCache",
        understanding_requirements=understanding,
        solution_overview=overview,
        solution_architecture=architecture,
        oem_solution_reviews=[oem_review]
    )

@pytest.fixture
def minimal_technical_proposal_data():
    understanding = UnderstandingRequirements(content="Client needs a simple static website.")
    overview = SolutionOverview(content="A static site using HTML, CSS, and JavaScript.")
    architecture = SolutionArchitecture(
        descriptive_text="Standard web server hosting static files. No complex backend.",
        mermaid_script=None # No diagram needed
    )
    return Proposal(
        target_technology="HTML, CSS, JavaScript",
        understanding_requirements=understanding,
        solution_overview=overview,
        solution_architecture=architecture
        # oem_solution_reviews is None by default
    )

def test_formatting_agent_instantiation_revised():
    agent = FormattingAgent()
    assert agent is not None

def test_format_full_technical_proposal(sample_technical_proposal_data):
    agent = FormattingAgent()
    markdown = agent.format_proposal_to_markdown(sample_technical_proposal_data)

    assert "**Based on RFP:** ClientRFP-Tech-002.pdf" in markdown
    assert "**Proposed Technology Focus:** Python, React, Microservices & AmazingCache" in markdown
    assert "---" in markdown # Separator

    assert "# Understanding of Requirements" in markdown
    assert "client requires a robust e-commerce platform" in markdown

    assert "# Solution Overview" in markdown
    assert "cloud-native microservices architecture" in markdown

    assert "# Solution Architecture" in markdown
    assert "system will have a presentation layer" in markdown
    assert "**Reference Architecture Diagram:**" in markdown
    assert "```mermaid\ngraph TD;" in markdown
    assert "User --> Frontend;" in markdown
    assert "```" in markdown.split("User --> Frontend;")[1] # Ensure closing backticks for mermaid

    assert "## Overview: AmazingCache" in markdown # OEM Review is H2
    assert "distributed caching solution" in markdown

    # Check order (simple check)
    pos_understanding = markdown.find("# Understanding of Requirements")
    pos_overview = markdown.find("# Solution Overview")
    pos_architecture = markdown.find("# Solution Architecture")
    pos_oem = markdown.find("## Overview: AmazingCache")

    assert 0 < pos_understanding < pos_overview < pos_architecture < pos_oem, "Sections seem to be out of order or missing."

def test_format_minimal_technical_proposal(minimal_technical_proposal_data):
    agent = FormattingAgent()
    markdown = agent.format_proposal_to_markdown(minimal_technical_proposal_data)

    assert "**Proposed Technology Focus:** HTML, CSS, JavaScript" in markdown
    assert "# Understanding of Requirements" in markdown
    assert "Client needs a simple static website." in markdown
    assert "# Solution Overview" in markdown
    assert "static site using HTML, CSS, and JavaScript." in markdown
    assert "# Solution Architecture" in markdown
    assert "Standard web server hosting static files." in markdown

    assert "Reference Architecture Diagram:" not in markdown # No mermaid script
    assert "OEM Solution Reviews" not in markdown # No OEM reviews
    assert "Overview:" not in markdown # Specific to OEM title

def test_format_proposal_architecture_no_mermaid(minimal_technical_proposal_data):
    # Uses minimal_technical_proposal_data which has no mermaid script
    agent = FormattingAgent()
    markdown = agent.format_proposal_to_markdown(minimal_technical_proposal_data)
    assert "# Solution Architecture" in markdown
    assert "Standard web server hosting static files." in markdown
    assert "```mermaid" not in markdown
    assert "**Reference Architecture Diagram:**" not in markdown

def test_format_proposal_architecture_with_unwrapped_mermaid():
    agent = FormattingAgent()
    understanding = UnderstandingRequirements(content="Reqs.")
    overview = SolutionOverview(content="Overview.")
    architecture_unwrapped = SolutionArchitecture(
        descriptive_text="Architecture with unwrapped Mermaid.",
        mermaid_script="graph TD;\n  A --> B;" # Missing backticks and language specifier
    )
    proposal = Proposal(
        target_technology="Test Mermaid Wrapping",
        understanding_requirements=understanding,
        solution_overview=overview,
        solution_architecture=architecture_unwrapped
    )
    markdown = agent.format_proposal_to_markdown(proposal)

    assert "# Solution Architecture" in markdown
    assert "**Reference Architecture Diagram:**" in markdown
    # Check if agent correctly wrapped it
    assert "```mermaid\ngraph TD;\n  A --> B;\n```" in markdown

def test_format_proposal_empty_sections_are_omitted():
    agent = FormattingAgent()
    proposal = Proposal(
        target_technology="Test Empty Sections",
        understanding_requirements=UnderstandingRequirements(content="  "), # Empty content
        solution_overview=SolutionOverview(content="Valid overview."),
        solution_architecture=SolutionArchitecture(descriptive_text="  ", mermaid_script=" ") # Empty content
    )
    markdown = agent.format_proposal_to_markdown(proposal)

    assert "Understanding of Requirements" not in markdown # Should be omitted
    assert "# Solution Overview" in markdown # Should be present
    assert "Valid overview." in markdown
    assert "Solution Architecture" not in markdown # Both text and mermaid are empty/whitespace
