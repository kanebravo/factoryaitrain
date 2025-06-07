import streamlit as st
import os
import asyncio
import tempfile # To handle temporary file creation securely

from rfp_proposal_generator.generator import ProposalGenerator
from rfp_proposal_generator.utils.exceptions import (
    ProposalGenerationError,
    ConfigurationError,
    RFPParserError,
    LLMGenerationError
)

# Page Configuration
st.set_page_config(page_title="RFP Proposal Generator", layout="wide")

# Application Title
st.title("RFP Proposal Generator")

# Sidebar for Instructions and API Key Info
st.sidebar.header("Instructions")
st.sidebar.info(
    """
    1.  **Upload your RFP Document**: Supported formats are PDF (.pdf) and Markdown (.md).
    2.  **Enter Target Technology**: Specify the core technology for the proposal (e.g., "Python with FastAPI", "OutSystems Platform").
    3.  **Generate Proposal**: Click the button to start the generation process.
    4.  **Review Output**: The generated proposal will be displayed in Markdown format.
    """
)
st.sidebar.header("API Key Configuration")
st.sidebar.warning(
    """
    This application uses OpenAI's language models.
    Ensure your `OPENAI_API_KEY` is set in a `.env` file in the project's root directory
    (where this Streamlit app is run from), or that it's available as an environment variable.

    Example `.env` file content:
    ```
    OPENAI_API_KEY="your_actual_openai_api_key_here"
    ```
    """
)

# Main Area for Inputs
st.header("Inputs")
uploaded_file = st.file_uploader("1. Upload RFP Document", type=["pdf", "md"], help="Upload a PDF or Markdown file for the RFP.")
target_technology = st.text_input("2. Enter Target Technology", placeholder="e.g., Cloud-Native Web Application, Salesforce CRM", help="Specify the main technology or platform for the proposal.")

TEMP_DIR = "temp_rfps" # Define a temporary directory

if 'proposal_markdown' not in st.session_state:
    st.session_state.proposal_markdown = ""
if 'last_error' not in st.session_state:
    st.session_state.last_error = ""


if st.button("Generate Proposal", type="primary", help="Click to start generating the proposal based on the inputs."):
    st.session_state.proposal_markdown = "" # Clear previous results
    st.session_state.last_error = ""      # Clear previous errors

    if uploaded_file is not None and target_technology and target_technology.strip():
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
            st.toast(f"Created temporary directory: {TEMP_DIR}", icon="📁")

        # Save uploaded file to a temporary path
        # Using NamedTemporaryFile from tempfile module for better security and management
        try:
            with tempfile.NamedTemporaryFile(dir=TEMP_DIR, delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_file_path = tmp_file.name
            st.toast(f"RFP file '{uploaded_file.name}' saved temporarily.", icon="📄")

            with st.spinner("Generating proposal... This may take a few moments. Please wait."):
                try:
                    # Instantiate ProposalGenerator (can raise ConfigurationError)
                    generator = ProposalGenerator()

                    # Generate proposal (can raise ProposalGenerationError)
                    markdown_proposal = asyncio.run(
                        generator.generate_proposal(rfp_file_path=temp_file_path, target_technology=target_technology)
                    )
                    st.session_state.proposal_markdown = markdown_proposal
                    st.success("Proposal generated successfully!")

                except ConfigurationError as ce:
                    st.error(f"Configuration Error: {ce}")
                    st.session_state.last_error = f"Configuration Error: {ce}"
                except ProposalGenerationError as pge:
                    error_message = f"Proposal Generation Error at stage '{pge.stage}': {pge.message}"
                    if pge.original_exception:
                        error_message += f"\n  Original error: {type(pge.original_exception).__name__}: {pge.original_exception}"
                    st.error(error_message)
                    st.session_state.last_error = error_message
                except Exception as e: # Catch any other unexpected errors
                    st.error(f"An unexpected error occurred: {e.__class__.__name__} - {e}")
                    st.session_state.last_error = f"An unexpected error occurred: {e.__class__.__name__} - {e}"

        finally: # Ensure cleanup even if errors occur
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    st.toast(f"Temporary file '{os.path.basename(temp_file_path)}' cleaned up.", icon="🗑️")
                except Exception as e_clean:
                    st.warning(f"Could not clean up temporary file {temp_file_path}: {e_clean}")
    else:
        if not uploaded_file:
            st.error("Please upload an RFP file.")
            st.session_state.last_error = "Please upload an RFP file."
        if not target_technology or not target_technology.strip():
            st.error("Please enter the target technology.")
            st.session_state.last_error = "Please enter the target technology."


# Display Area for Output or Error
if st.session_state.proposal_markdown:
    st.header("Generated Proposal")
    st.markdown(st.session_state.proposal_markdown)
    st.download_button(
        label="Download Proposal as Markdown",
        data=st.session_state.proposal_markdown,
        file_name=f"proposal_{target_technology.replace(' ', '_') if target_technology else 'generic'}.md",
        mime="text/markdown"
    )
elif st.session_state.last_error: # Display error if generation failed and no markdown is present
    st.error(f"Last error during generation: {st.session_state.last_error}")

st.markdown("---")
st.markdown("Developed by an AI agent.")
