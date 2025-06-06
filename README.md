# RFP Proposal Generator

This project uses AI (Pydantic AI with OpenAI) to generate draft proposals based on an input RFP document (PDF or Markdown) and a specified technology focus.

## Features

*   Parses RFP files (PDF and Markdown).
*   Uses AI agents to:
    *   Review the RFP and extract key information (summary, requirements, evaluation criteria).
    *   Generate a technical solution section based on RFP requirements and a chosen technology.
*   Formats the generated content into a Markdown proposal.
*   Provides a Command-Line Interface (CLI) for easy use.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory_name>
    ```
    (Replace `<repository_url>` and `<repository_directory_name>` with actual values if known, otherwise use generic placeholders)

2.  **Create a virtual environment and activate it:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your OpenAI API Key:**
    Copy the `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```
    Then, edit the `.env` file and add your actual OpenAI API key:
    ```
    OPENAI_API_KEY="your_openai_api_key_here"
    ```

## CLI Usage

The main way to use the generator is through its command-line interface.

**Generate a proposal:**

```bash
python main.py generate --rfp-file path/to/your/rfp_document.md --technology "Your Chosen Technology" --output-file path/to/save/proposal.md
```

**CLI Options:**

*   `--rfp-file, -f TEXT`: Path to the RFP file (PDF or Markdown). (Required)
*   `--technology, -t TEXT`: The core technology for the proposal. (Required)
*   `--output-file, -o TEXT`: Path to save the generated Markdown proposal. If not provided, prints to console.
*   `--api-key, -k TEXT`: OpenAI API key. Overrides key from `.env`.
*   `--model, -m TEXT`: LLM model to use (e.g., 'openai:gpt-3.5-turbo', 'openai:gpt-4'). Default: 'openai:gpt-3.5-turbo'.
*   `--help`: Show help message and exit.

**Example:**

```bash
python main.py generate \
    --rfp-file examples/rfps/sample.md \
    --technology "Python with FastAPI and Vue.js" \
    --output-file examples/proposals/my_generated_proposal.md
```

This will read `examples/rfps/sample.md`, generate a proposal focused on "Python with FastAPI and Vue.js", and save the output to `examples/proposals/my_generated_proposal.md`.

If you omit `--output-file`, the proposal will be printed to your terminal.

Ensure `examples/rfps/sample.md` exists or use a path to your own RFP file.
The directory for `--output-file` will be created if it doesn't exist.
