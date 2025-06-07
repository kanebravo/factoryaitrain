import pytest
import os
import shutil
import asyncio
from rfp_proposal_generator.generator import ProposalGenerator
from rfp_proposal_generator.utils.exceptions import ProposalGenerationError

# Define the paths to test data relative to the tests directory or project root
# Assuming tests are run from the project root.
# If tests/test_integration/ is the CWD, paths need adjustment.
# For now, assume project root is CWD for pytest.
TEST_DATA_DIR = "tests/test_data/rfps"
SAMPLE_MD_RFP = os.path.join(TEST_DATA_DIR, "sample_rfp_integration.md")
# sample.pdf is in examples/rfps, not tests/test_data/rfps
SAMPLE_PDF_RFP = "examples/rfps/sample.pdf"

@pytest.fixture(scope="module")
def output_dir():
    """Create a temporary directory for test outputs and clean up after tests."""
    dir_path = "tests/test_output/integration_proposals"
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    os.makedirs(dir_path, exist_ok=True)
    yield dir_path
    # Clean up after tests run in the module
    # shutil.rmtree(dir_path) # Commented out for now to inspect outputs if needed

@pytest.fixture(scope="module")
def generator():
    """Provides a ProposalGenerator instance for the test module."""
    # Attempt to load .env if ProposalGenerator doesn't explicitly do it first
    # However, ProposalGenerator itself handles .env loading.
    # The main concern here is the API key for actual calls.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try loading from .env directly for the test environment
        from dotenv import load_dotenv
        if load_dotenv():
            api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment or .env file, skipping integration tests.")

    # If we reach here, ProposalGenerator's __init__ should find the key.
    # If it still raises ValueError, there's an issue with how it's looking for the key.
    try:
        return ProposalGenerator()
    except ValueError as e:
        # This might happen if .env is not in the expected place for ProposalGenerator
        # or if the key is truly missing despite .env loading attempts.
        pytest.skip(f"Skipping integration tests: ProposalGenerator init failed: {e}")

@pytest.mark.asyncio
async def test_generate_proposal_markdown_rfp(output_dir, generator: ProposalGenerator):
    """Test end-to-end proposal generation with a sample Markdown RFP."""
    rfp_file = SAMPLE_MD_RFP
    technology = "Cloud-Native Web Application with Microservices"
    output_filename = os.path.join(output_dir, "markdown_rfp_proposal.md")

    assert os.path.exists(rfp_file), f"Sample Markdown RFP not found at {rfp_file}"

    try:
        markdown_proposal = await generator.generate_proposal(
            rfp_file_path=rfp_file,
            target_technology=technology
        )
    except ProposalGenerationError as e:
        pytest.fail(f"Proposal generation failed with ProposalGenerationError: {e}")
    except Exception as e:
        pytest.fail(f"Proposal generation failed with an unexpected exception: {e}")

    assert markdown_proposal is not None, "Generated proposal content should not be None."
    assert len(markdown_proposal.strip()) > 0, "Generated proposal content should not be empty."

    # Optional: Save output and assert file creation
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown_proposal)
    assert os.path.exists(output_filename), f"Output file was not created at {output_filename}"
    assert os.path.getsize(output_filename) > 0, "Output file should not be empty."

    # Basic check for some expected content (very generic)
    assert "## 1. Understanding of Requirements" in markdown_proposal, "Markdown output missing 'Understanding of Requirements' section."
    assert "## 2. Solution Overview" in markdown_proposal, "Markdown output missing 'Solution Overview' section."
    assert technology in markdown_proposal, f"Target technology '{technology}' not found in the proposal."


@pytest.mark.asyncio
async def test_generate_proposal_oem_technology(output_dir, generator: ProposalGenerator):
    """Test proposal generation with an OEM technology to ensure OEM review section is included."""
    rfp_file = SAMPLE_MD_RFP
    oem_technology = "OutSystems Platform" # Example of an OEM technology
    output_filename = os.path.join(output_dir, "oem_rfp_proposal.md")

    assert os.path.exists(rfp_file), f"Sample Markdown RFP not found at {rfp_file}"

    try:
        markdown_proposal = await generator.generate_proposal(
            rfp_file_path=rfp_file,
            target_technology=oem_technology
        )
    except ProposalGenerationError as e:
        pytest.fail(f"Proposal generation failed for OEM tech with ProposalGenerationError: {e}")
    except Exception as e:
        pytest.fail(f"Proposal generation failed for OEM tech with an unexpected exception: {e}")

    assert markdown_proposal is not None
    assert len(markdown_proposal.strip()) > 0

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown_proposal)
    assert os.path.exists(output_filename)

    # Check for OEM-specific section. The title might be "Overview: OutSystems Platform" or similar.
    # The FormattingAgent creates Level 2 heading for OEM reviews.
    assert f"## Overview: {oem_technology}" in markdown_proposal or \
           "## OEM Solution Review" in markdown_proposal or \
           f"Overview: {oem_technology}" in markdown_proposal, \
           f"OEM review section for '{oem_technology}' not found or title mismatch in the proposal."
    assert oem_technology in markdown_proposal, f"OEM technology '{oem_technology}' not found in the proposal."

# Placeholder for PDF test - will complete in next step
@pytest.mark.asyncio
async def test_generate_proposal_pdf_rfp(output_dir, generator: ProposalGenerator):
    """Test end-to-end proposal generation with a sample PDF RFP."""
    rfp_file = SAMPLE_PDF_RFP
    technology = "Secure Document Management System"
    output_filename = os.path.join(output_dir, "pdf_rfp_proposal.md")

    if not os.path.exists(rfp_file):
        pytest.skip(f"Sample PDF RFP not found at {rfp_file}. Skipping PDF integration test.")
        return

    try:
        markdown_proposal = await generator.generate_proposal(
            rfp_file_path=rfp_file,
            target_technology=technology
        )
    except ProposalGenerationError as e:
        pytest.fail(f"Proposal generation failed for PDF RFP with ProposalGenerationError: {e}")
    except Exception as e:
        pytest.fail(f"Proposal generation failed for PDF RFP with an unexpected exception: {e}")

    assert markdown_proposal is not None
    assert len(markdown_proposal.strip()) > 0

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown_proposal)
    assert os.path.exists(output_filename)
    assert "## 1. Understanding of Requirements" in markdown_proposal


def test_generate_proposal_non_existent_rfp(generator: ProposalGenerator):
    """Test error handling for a non-existent RFP file."""
    non_existent_rfp_file = "tests/test_data/rfps/non_existent_rfp.md"
    technology = "Any Technology"

    with pytest.raises(ProposalGenerationError) as excinfo:
        asyncio.run(generator.generate_proposal(
            rfp_file_path=non_existent_rfp_file,
            target_technology=technology
        ))

    assert "RFP file not found" in str(excinfo.value)
    assert non_existent_rfp_file in str(excinfo.value)
    assert excinfo.value.stage == "RFP Parsing"
    assert isinstance(excinfo.value.original_exception, FileNotFoundError)

# TODO: Add test for ConfigurationError if oem_keywords.json is missing/corrupt - this is harder to do
# as it's loaded at ProposalGenerator.__init__. Could mock fs or use a temp config path.
# For now, focusing on generate_proposal flow.
