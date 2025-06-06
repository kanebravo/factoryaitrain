import pytest
import os
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock

# Import the 'generate' command function from main.py
# To do this, we might need to ensure main.py can be imported.
# If main.py is in the root, and tests are in tests/, Python's import path needs to be correct.
# One way is to add the project root to sys.path or structure as a package.
# For now, assume 'main' can be imported if tests are run from the project root (e.g., `pytest`)
# or if PYTHONPATH is set up. Let's try a direct import, assuming standard pytest discovery.
from main import generate as generate_cli_command # Renaming to avoid clash if pytest runs it directly

# Fixture to set a dummy OPENAI_API_KEY for CLI tests,
# so the CLI doesn't fail early on API key checks.
@pytest.fixture(autouse=True)
def set_dummy_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key_for_cli_test")

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_proposal_generator_instance(): # Renamed for clarity
    # This mock will be used to patch ProposalGenerator where it's instantiated in main.py
    # It needs an async generate_proposal method
    mock_instance = MagicMock()
    mock_instance.generate_proposal = AsyncMock(return_value="# Mocked Proposal Content from CLI Test")
    return mock_instance

# Patching 'rfp_proposal_generator.generator.ProposalGenerator' if main.py imports it that way,
# or 'main.ProposalGenerator' if main.py does 'from rfp_proposal_generator.generator import ProposalGenerator'.
# The latter is what's in main.py.
@patch('main.ProposalGenerator') # Path to ProposalGenerator as imported in main.py
def test_cli_generate_successful_output_to_file(
    MockedProposalGenerator, # This is the patched class
    mock_proposal_generator_instance, # This is our instance to be returned by the patched class
    runner,
    tmp_path # pytest fixture for temporary directory
):
    MockedProposalGenerator.return_value = mock_proposal_generator_instance # When ProposalGenerator() is called, return our mock

    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")
    output_file = tmp_path / "output_proposal.md"

    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', str(rfp_file),
            '--technology', 'TestTech',
            '--output-file', str(output_file)
            # API key and model use defaults or dummy from fixture
        ]
    )

    assert result.exit_code == 0, f"CLI Error: {result.output}"
    assert "Initializing RFP Proposal Generator CLI..." in result.output
    assert f"Using RFP file: {str(rfp_file)}" in result.output
    assert "Target technology: TestTech" in result.output
    assert "Generating proposal..." in result.output
    assert f"Proposal successfully generated and saved to {str(output_file)}" in result.output

    # Verify ProposalGenerator was called correctly
    # The call to __init__ is on MockedProposalGenerator
    MockedProposalGenerator.assert_called_once_with(
        openai_api_key="dummy_key_for_cli_test", # From fixture via os.getenv in CLI
        llm_model_name="openai:gpt-3.5-turbo"  # Default model
    )

    # The call to generate_proposal is on the instance
    mock_proposal_generator_instance.generate_proposal.assert_called_once_with(
        rfp_file_path=str(rfp_file),
        target_technology='TestTech'
    )

    assert output_file.read_text() == "# Mocked Proposal Content from CLI Test"

@patch('main.ProposalGenerator')
def test_cli_generate_successful_output_to_console(
    MockedProposalGenerator,
    mock_proposal_generator_instance,
    runner,
    tmp_path
):
    MockedProposalGenerator.return_value = mock_proposal_generator_instance

    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")

    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', str(rfp_file),
            '--technology', 'ConsoleTech'
            # No --output-file
        ]
    )

    assert result.exit_code == 0, f"CLI Error: {result.output}"
    assert "--- GENERATED PROPOSAL ---" in result.output
    assert "# Mocked Proposal Content from CLI Test" in result.output
    assert "--- END OF PROPOSAL ---" in result.output

    MockedProposalGenerator.assert_called_once() # Check __init__
    mock_proposal_generator_instance.generate_proposal.assert_called_once_with(
        rfp_file_path=str(rfp_file),
        target_technology='ConsoleTech'
    )

def test_cli_missing_rfp_file(runner):
    result = runner.invoke(generate_cli_command, ['--technology', 'SomeTech'])
    assert result.exit_code != 0 # Expect non-zero for error
    assert "Error: Missing option '--rfp-file' / '-f'." in result.output # Click's error message

def test_cli_missing_technology(runner, tmp_path):
    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")
    result = runner.invoke(generate_cli_command, ['--rfp-file', str(rfp_file)])
    assert result.exit_code != 0
    assert "Error: Missing option '--technology' / '-t'." in result.output

@patch('main.os.getenv') # Mock os.getenv to control API key presence
@patch('main.ProposalGenerator') # Still need to mock this to prevent actual generation
def test_cli_missing_api_key(
    MockedProposalGenerator,
    mock_os_getenv,
    runner,
    tmp_path
):
    # Simulate os.getenv("OPENAI_API_KEY") returning None within the CLI command's scope
    # This is to test the CLI's specific API key check.
    # The autouse fixture `set_dummy_openai_api_key` sets the env var for the test session,
    # but `main.generate()` calls `os.getenv` itself. This patch targets that call.

    # Configure mock_os_getenv:
    # - Return "dummy_key_for_cli_test" for any getenv call *except* for "OPENAI_API_KEY"
    # - For "OPENAI_API_KEY", make it return None to simulate it being unset.
    def getenv_side_effect(key, default=None):
        if key == "OPENAI_API_KEY":
            return None # Simulate API key not being found by this specific call
        return os.environ.get(key, default) # For other env vars, use actual values

    mock_os_getenv.side_effect = getenv_side_effect

    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")

    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', str(rfp_file),
            '--technology', 'NoKeyTech'
            # No --api-key provided via CLI
        ]
    )

    # In Click, if a command function itself doesn't raise SystemExit,
    # but simply returns (like after printing an error message),
    # the exit_code of the result might be 0.
    # We should check the content of result.output for the error message.
    assert "Error: OpenAI API key not found." in result.output
    # And ensure the ProposalGenerator was not called if API key is missing
    MockedProposalGenerator.assert_not_called()


@patch('main.ProposalGenerator')
def test_cli_custom_api_key_and_model(
    MockedProposalGenerator,
    mock_proposal_generator_instance,
    runner,
    tmp_path
):
    MockedProposalGenerator.return_value = mock_proposal_generator_instance

    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")

    custom_api_key = "cli_provided_key"
    custom_model = "openai:gpt-4-test"

    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', str(rfp_file),
            '--technology', 'CustomKeyTech',
            '--api-key', custom_api_key,
            '--model', custom_model
        ]
    )

    assert result.exit_code == 0, f"CLI Error: {result.output}"
    MockedProposalGenerator.assert_called_once_with(
        openai_api_key=custom_api_key, # CLI key should be passed to generator
        llm_model_name=custom_model
    )
    mock_proposal_generator_instance.generate_proposal.assert_called_once()

# Test for FileNotFoundError when --rfp-file points to a non-existent file
def test_cli_rfp_file_not_exists(runner):
    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', 'non_existent_file.md',
            '--technology', 'SomeTech'
        ]
    )
    assert result.exit_code != 0
    assert "Error: Invalid value for '--rfp-file' / '-f': File 'non_existent_file.md' does not exist." in result.output # Changed "Path" to "File"

# Test for generic Exception handling in CLI (simulated)
@patch('main.ProposalGenerator')
def test_cli_generic_exception_handling(
    MockedProposalGenerator,
    mock_proposal_generator_instance, # Use the renamed fixture
    runner,
    tmp_path
):
    # Configure the mock generate_proposal to raise a generic Exception
    mock_proposal_generator_instance.generate_proposal.side_effect = Exception("Simulated generic error")
    MockedProposalGenerator.return_value = mock_proposal_generator_instance

    rfp_file = tmp_path / "sample_rfp.md"
    rfp_file.write_text("RFP Content")

    result = runner.invoke(
        generate_cli_command,
        [
            '--rfp-file', str(rfp_file),
            '--technology', 'ErrorTech'
        ]
    )
    assert result.exit_code == 0 # Should be 0 as the exception is caught and printed
    assert "An unexpected error occurred: Simulated generic error" in result.output
