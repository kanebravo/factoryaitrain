import json
import os
import logging
from typing import Dict, Any, Optional # Added Optional
from ..utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Define the expected keys for prompts to ensure all necessary prompts are loaded.
# This can be expanded as more prompts are managed.
EXPECTED_PROMPT_KEYS = [
    "rfp_review",
    "understanding_requirements",
    "solution_overview",
    "solution_architecture_text",
    "solution_architecture_mermaid",
    "oem_review"
]

def load_prompts(prompts_file_path: Optional[str] = None) -> Dict[str, str]:
    """
    Loads prompts from a JSON file.

    Args:
        prompts_file_path: Optional path to the prompts JSON file.
                           If None, uses default path relative to this util.

    Returns:
        A dictionary where keys are prompt identifiers and values are prompt strings.

    Raises:
        ConfigurationError: If the prompts file cannot be loaded, is malformed,
                            or if essential prompt keys are missing and no defaults are provided.
    """
    if prompts_file_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate up to 'rfp_proposal_generator' and then into 'config'
        base_dir = os.path.dirname(current_dir)
        prompts_file_path = os.path.join(base_dir, "config", "prompts.json")

    try:
        logger.info(f"Attempting to load prompts from: {prompts_file_path}")
        with open(prompts_file_path, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)

        # Validate that all expected prompts are present
        missing_keys = [key for key in EXPECTED_PROMPT_KEYS if key not in prompts_data]
        if missing_keys:
            err_msg = f"Missing essential prompt keys in {prompts_file_path}: {', '.join(missing_keys)}"
            logger.error(err_msg)
            # Depending on strictness, could fall back to defaults here if they were passed or loaded from another source
            raise ConfigurationError(err_msg)

        # Further validation: ensure all loaded prompts are strings
        for key, value in prompts_data.items():
            if not isinstance(value, str):
                err_msg = f"Invalid type for prompt '{key}' in {prompts_file_path}. Expected string, got {type(value).__name__}."
                logger.error(err_msg)
                raise ConfigurationError(err_msg)

        logger.info(f"Successfully loaded {len(prompts_data)} prompts from {prompts_file_path}")
        return prompts_data

    except FileNotFoundError:
        err_msg = f"Prompts file not found at {prompts_file_path}."
        logger.error(err_msg)
        raise ConfigurationError(err_msg) from None
    except json.JSONDecodeError as e:
        err_msg = f"Error decoding JSON from prompts file {prompts_file_path}: {e}."
        logger.error(err_msg)
        raise ConfigurationError(err_msg) from e
    except Exception as e: # Catch any other unexpected error
        err_msg = f"An unexpected error occurred while loading prompts from {prompts_file_path}: {e}."
        logger.error(err_msg)
        raise ConfigurationError(err_msg) from e

if __name__ == '__main__':
    # Example of how to use load_prompts
    # This assumes execution from the project root or that PYTHONPATH is set up.
    # For direct execution within utils, path adjustments might be needed for the default.

    # To make this runnable for simple testing from anywhere, provide a relative path
    # Assuming 'rfp_proposal_generator' is a top-level directory in the project.
    # This example might need adjustment based on actual execution context.
    try:
        # Path for testing assuming utils/config_loader.py is run from project root,
        # or using a path that works from where it's executed.
        # For testing, let's assume prompts.json is in rfp_proposal_generator/config/
        # This relative path works if main.py is in the root of the project.
        # If running config_loader.py directly, the default path logic inside load_prompts should work.

        print("Attempting to load prompts using default path logic within load_prompts...")
        loaded_prompts = load_prompts()
        print(f"Successfully loaded {len(loaded_prompts)} prompts.")
        if "rfp_review" in loaded_prompts:
            print("\nSample prompt (rfp_review):")
            print(loaded_prompts["rfp_review"][:200] + "...") # Print first 200 chars

    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Example of loading with an explicit (but still relative for testing) path
    # This assumes you have a prompts.json at rfp_proposal_generator/config/prompts.json
    # explicit_path = "rfp_proposal_generator/config/prompts.json"
    # if os.path.exists(explicit_path):
    #     print(f"\nAttempting to load prompts using explicit path: {explicit_path}...")
    #     try:
    #         loaded_prompts_explicit = load_prompts(prompts_file_path=explicit_path)
    #         print(f"Successfully loaded {len(loaded_prompts_explicit)} prompts using explicit path.")
    #     except ConfigurationError as e:
    #         print(f"Configuration Error with explicit path: {e}")
    # else:
    #     print(f"\nSkipping explicit path test, file not found: {explicit_path}")
