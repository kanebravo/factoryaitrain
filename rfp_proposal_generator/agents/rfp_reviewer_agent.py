import logging # Added for logging
from pydantic import BaseModel, Field
from typing import List, Optional

from pydantic_ai import Agent as PydanticAgent

from ..models.rfp_models import RFP, RFPSection
from .base_agent import AgentBase
from ..utils.exceptions import LLMGenerationError, ConfigurationError
from ..utils.config_loader import load_prompts

logger = logging.getLogger(__name__)

# Define the Pydantic model that the LLM should output for RFP review
class RFPReviewResult(BaseModel):
    summary: str = Field(description="A concise summary of the RFP's main goals and scope.")
    key_requirements: List[str] = Field(description="A list of the most critical requirements mentioned in the RFP.")
    evaluation_criteria: List[str] = Field(description="A list of criteria that will be used to evaluate the proposals, as stated in the RFP.")

class RFPReviewerAgent(AgentBase):
    DEFAULT_PROMPTS = {
        "rfp_review": """Given {context_description} below, please analyze it and extract the requested information.
Focus on identifying the main goals, critical requirements, and how proposals will be evaluated based *only* on the text provided.
If the provided text is noted as a chunk of a larger document, be aware that some information might be incomplete or continued in subsequent chunks.

Provided Text:
---
{source_text}
---

Please provide a concise summary, a list of key requirements, and a list of evaluation criteria based on the text above.
If certain information (e.g. evaluation criteria) is not present in this specific text, indicate that or return an empty list for that field."""
    }

    def __init__(self, llm_model_name: str = "openai:gpt-3.5-turbo"):
        super().__init__(model_name=llm_model_name)
        self.structured_llm_agent = PydanticAgent(
            model=self.model_name,
            output_type=RFPReviewResult
        )

        try:
            loaded_prompts = load_prompts()
            self.rfp_review_prompt = loaded_prompts.get("rfp_review", self.DEFAULT_PROMPTS["rfp_review"])
            if self.rfp_review_prompt == self.DEFAULT_PROMPTS["rfp_review"] and "rfp_review" not in loaded_prompts:
                 logger.warning("RFPReviewerAgent: 'rfp_review' prompt not found in prompts.json. Using default prompt.")
            elif self.rfp_review_prompt == self.DEFAULT_PROMPTS["rfp_review"] and "rfp_review" in loaded_prompts and loaded_prompts.get("rfp_review") != self.DEFAULT_PROMPTS["rfp_review"]:
                 logger.info("RFPReviewerAgent: 'rfp_review' prompt loaded from prompts.json is identical to default. This is fine.")
            else:
                 logger.info("RFPReviewerAgent: Successfully loaded 'rfp_review' prompt from prompts.json.")
        except ConfigurationError as e:
            logger.warning(f"RFPReviewerAgent: Failed to load prompts from JSON file ({e}). Using default prompts.")
            self.rfp_review_prompt = self.DEFAULT_PROMPTS["rfp_review"]
        except Exception as e: # Catch any other unexpected error during prompt loading
            logger.error(f"RFPReviewerAgent: An unexpected error occurred loading prompts: {e}. Using default prompts.")
            self.rfp_review_prompt = self.DEFAULT_PROMPTS["rfp_review"]


    async def review_rfp(self, rfp_document: RFP) -> RFP:
        '''
        Analyzes the RFP document using an LLM to extract summary, key requirements,
        and evaluation criteria. Updates the rfp_document object with this information.
        '''
        source_text = ""
        context_description = ""

        if rfp_document.text_chunks and len(rfp_document.text_chunks) > 0:
            source_text = rfp_document.text_chunks[0]
            context_description = "the first chunk of a Request for Proposal (RFP)"
            if len(rfp_document.text_chunks) > 1:
                context_description += " (note: this is only the first part of a larger document, focus on extracting information present in this chunk)"
            print(f"RFPReviewerAgent: Processing first text chunk (length: {len(source_text)} chars).")
        elif rfp_document.full_text:
            source_text = rfp_document.full_text
            context_description = "the full Request for Proposal (RFP) text"
            print(f"RFPReviewerAgent: Processing full text (length: {len(source_text)} chars).")
        else:
            raise ValueError("RFP document has no full_text or text_chunks to review.")

        # Limit source_text size for safety, e.g. to 15000 characters for this agent's purpose
        max_len = 15000
        if len(source_text) > max_len:
            source_text = source_text[:max_len]
            logger.info(f"RFPReviewerAgent: Truncated source text to {max_len} chars for LLM review.") # Changed print to logger.info

        final_prompt = self.rfp_review_prompt.format(
            context_description=context_description,
            source_text=source_text
        )

        try:
            review_result_container = await self.structured_llm_agent.run(
                user_prompt=final_prompt
            )

            if review_result_container and hasattr(review_result_container, 'output') and review_result_container.output:
                review_data: RFPReviewResult = review_result_container.output
                rfp_document.summary = review_data.summary
                rfp_document.key_requirements = review_data.key_requirements
                rfp_document.evaluation_criteria = review_data.evaluation_criteria
            else:
                # This case should ideally not happen if LLM call is successful and output parsing works
                err_msg = "LLM did not return the expected output structure or output was empty."
                logging.error(f"RFPReviewerAgent: {err_msg} - Container: {review_result_container}")
                raise LLMGenerationError(message=err_msg, agent_name="RFPReviewerAgent")

        except Exception as e: # Catch any exception from the LLM call or subsequent processing
            # Log the original error for debugging
            logging.error(f"RFPReviewerAgent: Error during RFP review LLM call: {e.__class__.__name__}: {e}")
            # Specific checks for OpenAI errors could be done here if pydantic-ai exposes them
            # For now, wrap the generic exception
            raise LLMGenerationError(
                message=f"Failed to review RFP due to an LLM error: {e}",
                agent_name="RFPReviewerAgent"
            ) from e

        return rfp_document

if __name__ == '__main__':
    import asyncio

    async def main_test():
        print("Testing RFPReviewerAgent...")
        # Ensure you have a .env file with OPENAI_API_KEY="your_key_here" in the project root

        dummy_rfp_content = """
        # Request for Proposal: New Website Design
        ## Summary
        We are seeking proposals for the redesign of our company website. The goal is to create a modern, responsive, and user-friendly site.
        ## Key Requirements
        - Mobile-first responsive design.
        - Integration with our existing CRM.
        - Content Management System (CMS) for easy updates.
        - SEO optimization.
        ## Evaluation Criteria
        - Portfolio of previous work (30%)
        - Technical approach and proposed solution (40%)
        - Price and value (20%)
        - Project timeline (10%)
        """
        sample_rfp = RFP(
            file_name="sample_rfp.md",
            full_text=dummy_rfp_content,
            sections=[RFPSection(title="Full Document", content=dummy_rfp_content)]
        )

        try:
            # This will use "openai:gpt-3.5-turbo" by default
            agent = RFPReviewerAgent()
            print("RFPReviewerAgent initialized with model:", agent.model_name)

            print(f"Reviewing RFP: {sample_rfp.file_name}")
            updated_rfp = await agent.review_rfp(sample_rfp)

            print("\n--- Review Results ---")
            if updated_rfp.summary:
                print(f"Summary: {updated_rfp.summary}")
                print(f"Key Requirements: {updated_rfp.key_requirements}")
                print(f"Evaluation Criteria: {updated_rfp.evaluation_criteria}")
            else:
                print("Review did not populate summary. Check for errors or LLM issues.")

        except ValueError as ve:
            print(f"Setup Error: {ve}")
        except Exception as e:
            print(f"An error occurred during testing: {e}")

    if __name__ == '__main__':
        # Note: Running this directly might require OPENAI_API_KEY to be set
        # and accessible. The test environment mocks this.
        # For local testing, ensure .env is present in the directory from which you run:
        # python -m rfp_proposal_generator.agents.rfp_reviewer_agent
        asyncio.run(main_test())
