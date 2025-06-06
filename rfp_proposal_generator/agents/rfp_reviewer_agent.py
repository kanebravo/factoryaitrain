from pydantic import BaseModel, Field
from typing import List, Optional

from pydantic_ai import Agent as PydanticAgent # Correct import based on __init__.py

from ..models.rfp_models import RFP, RFPSection # RFPSection needed for main_test
from .base_agent import AgentBase

# Define the Pydantic model that the LLM should output for RFP review
class RFPReviewResult(BaseModel):
    summary: str = Field(description="A concise summary of the RFP's main goals and scope.")
    key_requirements: List[str] = Field(description="A list of the most critical requirements mentioned in the RFP.")
    evaluation_criteria: List[str] = Field(description="A list of criteria that will be used to evaluate the proposals, as stated in the RFP.")

class RFPReviewerAgent(AgentBase):
    def __init__(self, llm_model_name: str = "openai:gpt-3.5-turbo"): # Parameter renamed for clarity
        # AgentBase constructor now takes model_name and ensures API key is loaded
        super().__init__(model_name=llm_model_name)

        # Initialize the PydanticAgent for structured output
        # The OPENAI_API_KEY is picked up from the environment by PydanticAgent
        self.structured_llm_agent = PydanticAgent(
            model=self.model_name, # Pass the model name string (e.g., "openai:gpt-3.5-turbo")
            output_type=RFPReviewResult # Define the structured output model
        )

    async def review_rfp(self, rfp_document: RFP) -> RFP:
        '''
        Analyzes the RFP document using an LLM to extract summary, key requirements,
        and evaluation criteria. Updates the rfp_document object with this information.
        '''
        if not rfp_document.full_text:
            raise ValueError("RFP document full_text is empty. Cannot review.")

        prompt_template = f"""
        Given the following Request for Proposal (RFP) text, please analyze it and extract the requested information.
        Focus on identifying the main goals, critical requirements, and how proposals will be evaluated.

        RFP Text:
        ---
        {rfp_document.full_text[:15000]}
        ---

        Please provide a concise summary, a list of key requirements, and a list of evaluation criteria.
        """
        # The '[:15000]' is a crude way to limit context size for safety.

        try:
            # pydantic_ai.Agent.run is async
            # The output_type is already defined in the PydanticAgent constructor
            review_result_container: any # AgentRunResult[RFPReviewResult]
            review_result_container = await self.structured_llm_agent.run(
                user_prompt=prompt_template
                # output_type can also be specified here if not in constructor
            )

            # The actual result is in review_result_container.output
            if review_result_container and hasattr(review_result_container, 'output'):
                review_data: RFPReviewResult = review_result_container.output
                rfp_document.summary = review_data.summary
                rfp_document.key_requirements = review_data.key_requirements
                rfp_document.evaluation_criteria = review_data.evaluation_criteria
            else:
                # This case should ideally not happen if LLM call is successful and output parsing works
                print("Warning: LLM did not return expected output structure.")


            # Update the original RFP object with the extracted information
            # rfp_document.summary = review_result.summary
            # rfp_document.key_requirements = review_result.key_requirements # Handled by review_data
            # rfp_document.evaluation_criteria = review_result.evaluation_criteria # Handled by review_data

        except Exception as e:
            print(f"Error during RFP review with LLM: {e}")
            # Optionally, re-raise or return the rfp_document without updates
            pass # Fall through to return rfp_document, un-updated on error

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
