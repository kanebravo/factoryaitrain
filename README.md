# RFP Proposal Generator (Technically Focused)

This project uses AI (Pydantic AI with OpenAI) to generate **technically focused draft proposals** based on an input RFP document (PDF or Markdown) and a specified technology focus. The goal is to accelerate the creation of initial technical documentation for proposals.

## Features

*   Parses RFP files (PDF and Markdown) to extract text.
*   Uses AI agents to:
    *   Analyze the RFP and provide a summary, list key requirements, and identify evaluation criteria.
    *   Generate core technical sections for a proposal, including:
            *   **Understanding of Requirements**: A narrative based on the RFP analysis.
            *   **Solution Overview**: Describing the proposed technical solution.
            *   **Solution Architecture**: Including a textual description and a **Mermaid script** for a conceptual/reference architecture diagram.
            *   **OEM Solution Overview (if applicable)**: If the chosen technology is a specific OEM product (e.g., "OutSystems", "Salesforce"), a brief overview of that product is generated.
*   Formats the generated content into a clean Markdown proposal.
*   Provides a Command-Line Interface (CLI) for ease of use.

**Note:** This generator focuses on the *technical aspects* of a proposal. It does not currently generate sections like company profiles, detailed project timelines, milestones, or pricing.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory_name>
    ```
    (Replace `<repository_url>` and `<repository_directory_name>` with actual values)

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
*   `--technology, -t TEXT`: The core technology for the proposal (e.g., "Python with Django", "OutSystems Platform"). (Required)
*   `--output-file, -o TEXT`: Path to save the generated Markdown proposal. If not provided, prints to console.
*   `--api-key, -k TEXT`: OpenAI API key. Overrides key from `.env`.
*   `--model, -m TEXT`: LLM model to use (e.g., 'openai:gpt-3.5-turbo', 'openai:gpt-4-turbo-preview'). Default: 'openai:gpt-3.5-turbo'.
*   `--help`: Show help message and exit.

**Example:**

```bash
python main.py generate \
    --rfp-file examples/rfps/sample.md \
    --technology "Python with FastAPI and Vue.js" \
    --output-file examples/proposals/my_generated_proposal.md
```

If using an OEM technology like "OutSystems", the generator may also include a specific section reviewing that OEM product:
```bash
python main.py generate \
    --rfp-file examples/rfps/sample_oem_rfp.md \
    --technology "OutSystems Platform" \
    --output-file examples/proposals/my_outsystems_proposal.md
```

Ensure `examples/rfps/sample.md` (or your own RFP file) exists. The directory for `--output-file` will be created if it doesn't exist.
The output will be a Markdown file. Mermaid diagrams can be rendered by Markdown viewers/editors that support Mermaid (e.g., GitLab, some VS Code extensions).
