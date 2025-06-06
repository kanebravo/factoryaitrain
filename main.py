import asyncio
import os
import click
from dotenv import load_dotenv

from rfp_proposal_generator.generator import ProposalGenerator

if not load_dotenv(verbose=True):
    print("Warning: .env file not found or empty. OPENAI_API_KEY might not be set if not already in environment.")


@click.command()
@click.option(
    '--rfp-file', '-f',
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to the RFP file (PDF or Markdown)."
)
@click.option(
    '--technology', '-t',
    required=True,
    type=str,
    help="The core technology to be featured in the proposal (e.g., 'Python with Django', 'React Native')."
)
@click.option(
    '--output-file', '-o',
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Path to save the generated Markdown proposal. If not provided, prints to console."
)
@click.option(
    '--api-key', '-k',
    type=str,
    default=None,
    help="OpenAI API key. If not provided, uses OPENAI_API_KEY from .env or environment."
)
@click.option(
    '--model', '-m',
    type=str,
    default="openai:gpt-3.5-turbo", # Default model for the generator
    help="The LLM model to use (e.g., 'openai:gpt-3.5-turbo', 'openai:gpt-4')."
)
def generate(rfp_file: str, technology: str, output_file: str, api_key: str, model: str):
    """
    Generates an RFP proposal using AI based on a provided RFP document and target technology.
    """
    click.echo("Initializing RFP Proposal Generator CLI...")

    effective_api_key = api_key if api_key else os.getenv("OPENAI_API_KEY")

    if not effective_api_key:
        click.secho("Error: OpenAI API key not found. "
                    "Please provide it via --api-key option, or set OPENAI_API_KEY in your .env file.",
                    fg="red")
        return

    try:
        click.echo(f"Using RFP file: {rfp_file}")
        click.echo(f"Target technology: {technology}")
        click.echo(f"Using LLM model: {model}")
        if output_file:
            click.echo(f"Output will be saved to: {output_file}")

        generator = ProposalGenerator(openai_api_key=effective_api_key, llm_model_name=model)

        click.echo("Generating proposal... This may take a few moments.")

        markdown_proposal = asyncio.run(
            generator.generate_proposal(rfp_file_path=rfp_file, target_technology=technology)
        )

        if output_file:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                click.echo(f"Created output directory: {output_dir}")

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_proposal)
            click.secho(f"Proposal successfully generated and saved to {output_file}", fg="green")
        else:
            click.secho("\n--- GENERATED PROPOSAL ---", fg="blue", bold=True)
            click.echo(markdown_proposal)
            click.secho("\n--- END OF PROPOSAL ---", fg="blue", bold=True)
            click.echo("Proposal generated. To save to a file, use the --output-file option.")

    except ValueError as ve:
        click.secho(f"Error during proposal generation: {ve}", fg="red")
    except FileNotFoundError as fnfe:
        click.secho(f"Error: RFP file not found at {rfp_file}", fg="red")
    except Exception as e:
        click.secho(f"An unexpected error occurred: {e}", fg="red")
        # import traceback
        # click.echo(traceback.format_exc()) # Uncomment for detailed debugging

if __name__ == '__main__':
    generate()
