from pydantic import Field
from typing import List, Optional

from .base_agent import AgentBase # For LLM configuration
from ..models.proposal_models import TechnicalSolution # Output model for this agent
from pydantic_ai import Agent as PydanticAIAgent # Renamed to avoid conflict

# This agent will populate the TechnicalSolution model.
# The TechnicalSolution model itself is already defined in proposal_models.py

class TechnicalWriterAgent(AgentBase):
    def __init__(self, model_name: str = "openai:gpt-3.5-turbo"):
        super().__init__(model_name=model_name) # Pass model_name to AgentBase, which loads OPENAI_API_KEY
        # The output_type is implicitly handled by the Pydantic model passed to `run`
        self.llm_agent = PydanticAIAgent(
            model=self.model_name, # e.g., "openai:gpt-3.5-turbo" or "openai:gpt-4"
            # OPENAI_API_KEY is picked up from env by pydantic_ai.Agent
        )

    async def generate_technical_solution(
        self,
        key_requirements: List[str],
        chosen_technology: str,
        rfp_summary: Optional[str] = None
    ) -> TechnicalSolution:
        '''
        Generates the technical solution section of a proposal.

        Args:
            key_requirements: A list of key requirements extracted from the RFP.
            chosen_technology: The core technology the user wants to base the solution on.
            rfp_summary: An optional summary of the RFP for context.

        Returns:
            A TechnicalSolution Pydantic model instance.
        '''
        if not key_requirements:
            raise ValueError("Key requirements must be provided to generate a technical solution.")
        if not chosen_technology:
            raise ValueError("A chosen technology must be specified.")

        requirements_str = "- " + "\n- ".join(key_requirements)

        prompt_context = f"RFP Summary (if available): {rfp_summary}\n\n" if rfp_summary else ""

        prompt = f"""
        You are a technical writer tasked with drafting the 'Technical Solution' section of a project proposal.
        The client has provided a Request for Proposal (RFP) from which we have extracted the following key requirements and an overall summary.
        The proposed solution will be based on the technology: {chosen_technology}.

        {prompt_context}
        Key Requirements:
        {requirements_str}

        Based on these requirements and the specified technology ({chosen_technology}), please generate a compelling 'Technical Solution' section.
        This section should clearly explain how the chosen technology will be used to meet each key requirement.
        Describe the proposed architecture at a high level and briefly outline the implementation approach.
        The content should be professional, clear, and persuasive.
        Structure your response to fit the fields of the TechnicalSolution model: 'title' (which should be 'Technical Solution') and 'content'.
        Focus on providing detailed and practical information in the 'content' field.
        """

        try:
            # The PydanticAIAgent's `run` method will attempt to populate TechnicalSolution
            # The result from pydantic_ai.Agent.run() is an AgentRunResult object,
            # and the actual Pydantic model instance is in its 'output' attribute.
            run_result_container = await self.llm_agent.run(
                output_type=TechnicalSolution, # Specify the desired output Pydantic model
                user_prompt=prompt # Pass the prompt to user_prompt
            )

            # Ensure run_result_container and its output are not None before proceeding
            if run_result_container and hasattr(run_result_container, 'output') and run_result_container.output is not None:
                solution_output: TechnicalSolution = run_result_container.output
                # Ensure the title is set correctly, as the LLM might not always set it as "Technical Solution"
                solution_output.title = "Technical Solution"
                return solution_output
            else:
                # This case might occur if the LLM call fails in a way that PydanticAIAgent returns None
                # or an object without 'output', or if output itself is None.
                print(f"Error: LLM did not return the expected output structure. Container: {run_result_container}")
                return TechnicalSolution(title="Technical Solution", content="Error: Failed to generate content due to unexpected LLM response.")

        except Exception as e:
            print(f"Error during technical solution generation with LLM: {e}")
            # Fallback or re-raise
            return TechnicalSolution(title="Technical Solution", content=f"Error generating content: {e}")

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    async def main_test():
        print("Testing TechnicalWriterAgent...")
        # Ensure you have a .env file with OPENAI_API_KEY

        sample_requirements = [
            "Mobile-first responsive design.",
            "Integration with existing CRM.",
            "Content Management System (CMS) for easy updates."
        ]
        sample_technology = "React with a Headless CMS (e.g., Strapi)"
        sample_summary = "Client needs a new company website, modern and user-friendly."

        try:
            agent = TechnicalWriterAgent() # Loads .env
            print("TechnicalWriterAgent initialized.")

            print(f"Generating technical solution for technology: {sample_technology}")
            solution = await agent.generate_technical_solution(
                key_requirements=sample_requirements,
                chosen_technology=sample_technology,
                rfp_summary=sample_summary
            )

            print("\n--- Generated Technical Solution ---")
            print(f"Title: {solution.title}")
            print(f"Content:\n{solution.content}")

        except ValueError as ve:
            print(f"Setup or Input Error: {ve}")
        except Exception as e:
            print(f"An error occurred during testing: {e}")

    # To run this test snippet:
    # import asyncio
    # if __name__ == '__main__':
    #   # Make sure .env is in the root or accessible
    #   # from dotenv import load_dotenv
    #   # load_dotenv()
    #   asyncio.run(main_test())
    pass
