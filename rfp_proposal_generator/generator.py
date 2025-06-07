import os
import json # Added for loading OEM keywords
import logging # Added for logging
from typing import Optional, List # Added List

from .parsers.rfp_parser import RFPParser
from .agents.rfp_reviewer_agent import RFPReviewerAgent # Stays the same
from .agents.technical_writer_agent import TechnicalWriterAgent, TechnicalContentSet # TechnicalWriterAgent is revised
from .agents.formatting_agent import FormattingAgent # FormattingAgent is revised
from .models.rfp_models import RFP
from .utils.exceptions import ( # Import custom exceptions
    ConfigurationError, ProposalGenerationError, RFPParserError,
    LLMGenerationError, MermaidValidationError
)
# Import new proposal models
from .models.proposal_models import (
    Proposal, UnderstandingRequirements, SolutionOverview,
    SolutionArchitecture, OEMSolutionReview
)

class ProposalGenerator:
    DEFAULT_OEM_KEYWORDS = [ # Used as fallback
        "salesforce", "outsystems", "sap", "oracle",
        "microsoft dynamics", "servicenow", "workday"
    ]

    def __init__(self, openai_api_key: Optional[str] = None, llm_model_name: str = "openai:gpt-3.5-turbo"):
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        if not os.getenv("OPENAI_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv()
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY not found. Please set it in .env or pass it to ProposalGenerator.")

        self.rfp_parser = None
        self.rfp_reviewer_agent = RFPReviewerAgent(llm_model_name=llm_model_name)
        self.technical_writer_agent = TechnicalWriterAgent(model_name=llm_model_name)
        self.formatting_agent = FormattingAgent()
        try:
            self.oem_keywords = self._load_oem_keywords()
        except ConfigurationError as e:
            logging.error(f"Failed to initialize ProposalGenerator due to OEM keyword loading error: {e}")
            # Option: re-raise, or use defaults and allow startup. Task implies raising.
            raise # Or: self.oem_keywords = self.DEFAULT_OEM_KEYWORDS.copy(); logging.warning("Using default OEM keywords.")


    def _load_oem_keywords(self) -> List[str]:
        """Loads OEM keywords from the config file. Raises ConfigurationError on failure."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "config", "oem_keywords.json")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            keywords = data.get("oem_keywords")
            if isinstance(keywords, list) and all(isinstance(k, str) for k in keywords):
                logging.info(f"Successfully loaded OEM keywords from {config_path}")
                return keywords
            else:
                err_msg = f"Invalid format for 'oem_keywords' in {config_path}. Expected a list of strings."
                logging.error(err_msg)
                raise ConfigurationError(err_msg)
        except FileNotFoundError:
            err_msg = f"OEM keywords file not found at {config_path}."
            logging.error(err_msg)
            raise ConfigurationError(err_msg) from None # Use `from None` to break chain if desired
        except json.JSONDecodeError as e:
            err_msg = f"Error decoding JSON from {config_path}: {e}."
            logging.error(err_msg)
            raise ConfigurationError(err_msg) from e
        except Exception as e: # Catch any other unexpected error during loading
            err_msg = f"An unexpected error occurred while loading OEM keywords from {config_path}: {e}."
            logging.error(err_msg)
            raise ConfigurationError(err_msg) from e

    def _is_oem_technology(self, technology_name: str) -> bool:
        technology_name_lower = technology_name.lower()
        for keyword in self.oem_keywords: # Use loaded keywords
            if keyword.lower() in technology_name_lower: # Ensure keyword is also lowercased for comparison
                return True
        return False

    async def generate_proposal(self, rfp_file_path: str, target_technology: str) -> str:
        print(f"Starting technical proposal generation for RFP: {rfp_file_path} using technology: {target_technology}")

        try:
            print("Step 1: Parsing RFP...")
            self.rfp_parser = RFPParser(file_path=rfp_file_path) # Can raise FileNotFoundError
            parsed_rfp_doc: RFP = self.rfp_parser.parse() # Can raise RFPParserError
            if not parsed_rfp_doc.full_text or not parsed_rfp_doc.full_text.strip():
                # This specific check remains, as it's about content validity post-parsing
                raise RFPParserError(f"RFP file '{rfp_file_path}' parsed but resulted in empty content.")
        except FileNotFoundError as e:
            logging.error(f"RFP file not found: {rfp_file_path} - {e}")
            raise ProposalGenerationError(message=f"RFP file not found: {rfp_file_path}", stage="RFP Parsing", original_exception=e) from e
        except RFPParserError as e:
            logging.error(f"Failed to parse RFP: {e}")
            raise ProposalGenerationError(message=f"Failed to parse RFP file: {e}", stage="RFP Parsing", original_exception=e) from e

        log_message = f"RFP parsed. Extracted text length: {len(parsed_rfp_doc.full_text)}. "
        if parsed_rfp_doc.text_chunks:
            log_message += f"Document split into {len(parsed_rfp_doc.text_chunks)} text chunks."
            # Optional: log lengths of first few chunks for debugging if needed
            # for i, chunk in enumerate(parsed_rfp_doc.text_chunks[:3]):
            #    log_message += f"\n  Chunk {i+1} length: {len(chunk)}"
        else:
            log_message += "No text chunks were generated (document might be too short or empty)."
        # Use logging.info for this kind of operational detail, print for major steps.
        logging.info(log_message)
        # Keep print for major step
        print(f"RFP parsed. Extracted text length: {len(parsed_rfp_doc.full_text)}")

        try:
            print("Step 2: Reviewing RFP with RFPReviewerAgent...")
            reviewed_rfp_doc = await self.rfp_reviewer_agent.review_rfp(parsed_rfp_doc)
            if not reviewed_rfp_doc.summary and not reviewed_rfp_doc.key_requirements:
                 # This is a warning, not necessarily a fatal error for the whole process
                 logging.warning("RFP review did not yield a summary or key requirements. Proposal quality may be affected.")
            else:
                print(f"RFP review complete. Summary (first 100 chars): {reviewed_rfp_doc.summary[:100] if reviewed_rfp_doc.summary else 'N/A'}...")
                print(f"Key Requirements (first 2): {reviewed_rfp_doc.key_requirements[:2] if reviewed_rfp_doc.key_requirements else 'N/A'}...")
        except LLMGenerationError as e:
            logging.error(f"Error during RFP review stage: {e}")
            raise ProposalGenerationError(message=f"Error during RFP review: {e}", stage="RFP Review", original_exception=e) from e

        try:
            print("Step 3: Generating core technical content with TechnicalWriterAgent...")
            technical_content_set: TechnicalContentSet = await self.technical_writer_agent.generate_all_technical_content(
                rfp_full_text=parsed_rfp_doc.full_text, # Consider using chunks here in future if full_text is too large
                rfp_summary=reviewed_rfp_doc.summary,
                key_requirements=reviewed_rfp_doc.key_requirements or [],
                evaluation_criteria=reviewed_rfp_doc.evaluation_criteria,
                chosen_technology=target_technology
            )
            print("Core technical content generated.")
        except (LLMGenerationError, MermaidValidationError) as e: # MermaidValidationError is a subclass of LLMGenerationError
            logging.error(f"Error during technical content generation: {e}")
            raise ProposalGenerationError(message=f"Error during technical content generation: {e}", stage="Technical Content Generation", original_exception=e) from e

        oem_reviews_list: Optional[List[OEMSolutionReview]] = None
        if self._is_oem_technology(target_technology):
            try:
                print(f"Step 4a: Generating OEM review for {target_technology}...")
                oem_review = await self.technical_writer_agent.generate_oem_review(
                    oem_product_name=target_technology,
                    key_requirements=reviewed_rfp_doc.key_requirements,
                    rfp_summary=reviewed_rfp_doc.summary
                )
                oem_reviews_list = [oem_review]
                print(f"OEM review for {target_technology} generated.")
            except LLMGenerationError as e:
                logging.error(f"Error during OEM review generation for '{target_technology}': {e}")
                # Decide if this is fatal for the whole proposal or just skip this part
                # For now, let's make it fatal to ensure visibility of errors
                raise ProposalGenerationError(message=f"Error generating OEM review for '{target_technology}': {e}", stage="OEM Review Generation", original_exception=e) from e
        else:
            print("Step 4a: No specific OEM review triggered by target technology name.")

        # Step 5: Assembling (generally not prone to external errors unless data is malformed, caught by Pydantic)
        print("Step 5: Assembling technically-focused proposal document...")
        understanding_section = UnderstandingRequirements(
            content=technical_content_set.understanding_requirements_content
        )
        overview_section = SolutionOverview(
            content=technical_content_set.solution_overview_content
        )
        architecture_section = SolutionArchitecture(
            descriptive_text=technical_content_set.solution_architecture_descriptive_text,
            mermaid_script=technical_content_set.solution_architecture_mermaid_script
        )

        final_proposal_model = Proposal(
            rfp_reference_document=parsed_rfp_doc.file_name,
            target_technology=target_technology,
            understanding_requirements=understanding_section,
            solution_overview=overview_section,
            solution_architecture=architecture_section,
            oem_solution_reviews=oem_reviews_list
        )
        print("Technically-focused proposal model assembled.")

        print("Step 6: Formatting proposal to Markdown...")
        markdown_proposal = self.formatting_agent.format_proposal_to_markdown(final_proposal_model)
        print("Proposal formatted to Markdown successfully.")

        return markdown_proposal

if __name__ == '__main__':
    import asyncio # Required for async main
    from dotenv import load_dotenv # Required for main

    async def run_generator_test():
        sample_rfp_path = "examples/rfps/sample.md"
        if not os.path.exists(sample_rfp_path):
            os.makedirs(os.path.dirname(sample_rfp_path), exist_ok=True)
            with open(sample_rfp_path, "w", encoding="utf-8") as f: # Added encoding
                f.write("# Sample RFP for Revised Generator\n\n## Section 1: Introduction\nWe need a new system for managing tasks.\n\n## Section 2: Requirements\n- Must be web-based.\n- Must support user accounts.\n- Must allow task creation and assignment.\n\n## Section 3: Evaluation\n- Ease of use\n- Scalability")
            print(f"Created dummy {sample_rfp_path} for testing.")

        target_tech_oem = "OutSystems Platform"

        print("Attempting to initialize ProposalGenerator (Revised)...")
        try:
            load_dotenv()
            if not os.getenv("OPENAI_API_KEY"):
                print("FATAL: OPENAI_API_KEY not set. Please create a .env file in the project root with your key.")
                return

            generator = ProposalGenerator()
            print("ProposalGenerator (Revised) initialized.")

            print(f"Generating proposal for {sample_rfp_path} with technology {target_tech_oem}...")
            markdown_output = await generator.generate_proposal(sample_rfp_path, target_tech_oem)

            print("\n========== GENERATED PROPOSAL (Markdown - Revised) ==========")
            print(markdown_output)
            print("=============================================================")

            output_filename = "examples/proposals/generated_proposal_revised_test.md"
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(markdown_output)
            print(f"Proposal saved to {output_filename}")

        except ValueError as ve:
            print(f"ValueError during generation: {ve}")
        except ImportError as ie:
            print(f"ImportError: {ie}")
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred: {e}")
            print(traceback.format_exc())

    if __name__ == '__main__':
        asyncio.run(run_generator_test())
