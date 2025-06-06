from pydantic import BaseModel, Field
from typing import List, Optional

from .base_agent import AgentBase # For LLM configuration
# Import the new models this agent will populate/return parts of
from ..models.proposal_models import UnderstandingRequirements, SolutionOverview, SolutionArchitecture, OEMSolutionReview
from pydantic_ai import Agent as PydanticAIAgent

# Define a new Pydantic model that represents the collective output of this agent
class TechnicalContentSet(BaseModel):
    understanding_requirements_content: str = Field(description="Narrative understanding of client requirements, derived from RFP analysis.")
    solution_overview_content: str = Field(description="Detailed overview of the proposed solution.")
    solution_architecture_descriptive_text: str = Field(description="Textual description of the solution architecture.")
    solution_architecture_mermaid_script: str = Field(description="Mermaid script for the solution architecture diagram. Should be enclosed in ```mermaid ... ```.")
    # OEM reviews will be handled slightly differently; the agent will generate a list of OEMSolutionReview objects.

class TechnicalWriterAgent(AgentBase):
    def __init__(self, model_name: str = "openai:gpt-3.5-turbo"):
        super().__init__(model_name=model_name) # Pass model_name to AgentBase, which loads OPENAI_API_KEY
        self.llm_agent = PydanticAIAgent(
            model=self.model_name, # e.g., "openai:gpt-3.5-turbo" or "openai:gpt-4"
            # OPENAI_API_KEY is picked up from env by pydantic_ai.Agent
            # llm_provider_api_key=self.api_key # This was removed in a previous step, which is correct.
        )

    async def generate_all_technical_content(
        self,
        rfp_full_text: str,
        rfp_summary: Optional[str],
        key_requirements: List[str],
        evaluation_criteria: Optional[List[str]],
        chosen_technology: str,
    ) -> TechnicalContentSet:
        '''
        Generates all core technical content for the proposal.
        '''
        if not rfp_full_text and not rfp_summary and not key_requirements:
            raise ValueError("Some RFP context (full text, summary, or key requirements) must be provided.")
        if not chosen_technology:
            raise ValueError("A chosen technology must be specified.")

        requirements_str = "- " + "\n- ".join(key_requirements) if key_requirements else "Not explicitly listed."
        criteria_str = "- " + "\n- ".join(evaluation_criteria) if evaluation_criteria else "Not explicitly listed."
        summary_str = rfp_summary if rfp_summary else "No summary provided."

        max_rfp_text_len = 10000
        truncated_rfp_text = rfp_full_text[:max_rfp_text_len]
        if len(rfp_full_text) > max_rfp_text_len:
            truncated_rfp_text += "\n... [RFP text truncated for brevity]"

        prompt = f"""
        You are a senior technical writer and solution architect. Based on the provided Request for Proposal (RFP) details and the chosen primary technology, generate the core technical sections of a proposal.

        **Chosen Primary Technology:** {chosen_technology}

        **RFP Details:**
        *   RFP Full Text (truncated): {truncated_rfp_text}
        *   RFP Summary: {summary_str}
        *   Key Client Requirements:
            {requirements_str}
        *   Evaluation Criteria (if known):
            {criteria_str}

        **Output Requirements:**
        Please generate content for the following sections, ensuring professional language and technical depth.
        The entire response should be structured as a single JSON object matching the Pydantic model `TechnicalContentSet`.

        1.  **understanding_requirements_content**:
            Write a narrative that demonstrates a clear understanding of the client's needs and objectives as expressed in the RFP. Synthesize information from the RFP summary, key requirements, and overall text. This should not just be a list but a thoughtful interpretation.

        2.  **solution_overview_content**:
            Provide a detailed overview of the proposed solution. Explain how it addresses the client's main problems/objectives using the "{chosen_technology}". Describe the core components, functionalities, and benefits of your proposed solution.

        3.  **solution_architecture_descriptive_text**:
            Describe the proposed solution architecture. Detail the main components, layers, interactions, and data flows. Explain how the "{chosen_technology}" fits into this architecture.

        4.  **solution_architecture_mermaid_script**:
            Generate a Mermaid diagram script (enclosed in ```mermaid ... ```) representing the conceptual or reference architecture described above. The diagram should be clear, concise, and accurately reflect the textual description. For example:
            ```mermaid
            graph TD;
                UserInterface --> API_Gateway;
                API_Gateway --> Microservice1;
                API_Gateway --> Microservice2;
                Microservice1 --> Database;
                Microservice2 --> Database;
                Microservice2 --> ExternalService;
            ```
            Ensure the Mermaid syntax is correct. Use common diagram types like `graph TD`, `sequenceDiagram`, or `classDiagram` as appropriate.

        **Example of the expected JSON output structure (do not include this example in your actual response):**
        ```json
        {{
            "understanding_requirements_content": "Based on the RFP, the client requires a scalable and user-friendly platform to streamline their data processing workflows. Key needs include real-time analytics, integration with existing systems, and robust security measures. Our understanding is that the primary goal is to enhance operational efficiency and decision-making capabilities.",
            "solution_overview_content": "We propose a cloud-native solution leveraging {chosen_technology}. This solution will consist of a data ingestion pipeline, a processing engine, and an analytics dashboard. It directly addresses the need for scalability and real-time data by utilizing microservices architecture and {chosen_technology}'s advanced features...",
            "solution_architecture_descriptive_text": "The architecture comprises three main layers: Data Ingestion Layer (handling data from various sources), Processing Layer (where {chosen_technology} performs core logic), and Presentation Layer (analytics and reporting). Data flows from ingestion through processing to presentation, with security measures at each stage.",
            "solution_architecture_mermaid_script": "```mermaid\ngraph TD;\n    A[Data Sources] --> B(Ingestion Layer);\n    B --> C{{Processing Engine - {chosen_technology}}};\n    C --> D[Analytics Dashboard];\n    C --> E(Data Warehouse);\n```"
        }}
        ```
        Focus on providing comprehensive, accurate, and well-written content for each field.
        If "{chosen_technology}" is a specific OEM product (e.g., "OutSystems", "Salesforce"), tailor the descriptions and architecture to reflect its typical usage and strengths.
        """

        try:
            run_result_container = await self.llm_agent.run( # Renamed from generated_content for clarity
                output_type=TechnicalContentSet,
                user_prompt=prompt, # prompt is passed as user_prompt
            )
            if run_result_container and hasattr(run_result_container, 'output') and run_result_container.output is not None:
                return run_result_container.output
            else:
                print(f"Error: LLM did not return the expected output structure for TechnicalContentSet. Container: {run_result_container}")
                raise Exception("Failed to generate technical content due to unexpected LLM response for TechnicalContentSet.")

        except Exception as e:
            print(f"Error during technical content generation with LLM: {e}")
            return TechnicalContentSet(
                understanding_requirements_content=f"Error generating content: {e}",
                solution_overview_content=f"Error generating content: {e}",
                solution_architecture_descriptive_text=f"Error generating content: {e}",
                solution_architecture_mermaid_script="```mermaid\ngraph TD;\n  Error[Error generating diagram];\n```"
            )

    async def generate_oem_review(
        self,
        oem_product_name: str,
        key_requirements: Optional[List[str]] = None,
        rfp_summary: Optional[str] = None
    ) -> OEMSolutionReview:
        '''
        Generates a review for a specific OEM product.
        '''
        if not oem_product_name:
            raise ValueError("OEM product name must be provided.")

        requirements_str = ("\nKey RFP Requirements for context (if available):\n- " + "\n- ".join(key_requirements)) if key_requirements else ""
        summary_str = f"\nRFP Summary for context (if available): {rfp_summary}" if rfp_summary else ""

        prompt = f"""
        You are a technical writer. Please generate an overview of the OEM product: "{oem_product_name}".
        This overview will be part of a larger project proposal.
        Describe what the product is, its main features, and its general benefits.
        If context from an RFP is provided below, briefly mention how this product might be relevant.

        {summary_str}
        {requirements_str}

        Structure your response to fit the fields of the OEMSolutionReview model: 'oem_product_name' (which is "{oem_product_name}"), 'title', and 'content'.
        The 'title' should be something like "Overview: {oem_product_name}".
        The 'content' should be the detailed overview.
        """
        try:
            run_result_container = await self.llm_agent.run( # Renamed for clarity
                output_type=OEMSolutionReview,
                user_prompt=prompt,
            )
            if run_result_container and hasattr(run_result_container, 'output') and run_result_container.output is not None:
                review_output: OEMSolutionReview = run_result_container.output
                review_output.oem_product_name = oem_product_name
                if not review_output.title or review_output.title == "OEM Product Overview":
                     review_output.title = f"Overview: {oem_product_name}"
                return review_output
            else:
                print(f"Error: LLM did not return the expected output structure for OEMReview for {oem_product_name}. Container: {run_result_container}")
                raise Exception(f"Failed to generate OEM review for {oem_product_name} due to unexpected LLM response.")
        except Exception as e:
            print(f"Error during OEM solution review generation for {oem_product_name}: {e}")
            return OEMSolutionReview(
                oem_product_name=oem_product_name,
                title=f"Overview: {oem_product_name}",
                content=f"Error generating review for {oem_product_name}: {e}"
            )

# Example Usage (for testing purposes within the file)
if __name__ == '__main__':
    import asyncio
    import os
    from dotenv import load_dotenv

    async def main_test():
        print("Testing TechnicalWriterAgent (Revised)...")
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            print("FATAL: OPENAI_API_KEY not found. Please set it in .env file.")
            return

        sample_rfp_text = "Our company seeks a new CRM system. It must be cloud-based, support sales and marketing, and integrate with our accounting software. We need mobile access and custom reporting. The goal is to improve sales productivity by 20%."
        sample_summary = "Client needs a new cloud-based CRM for sales/marketing with accounting integration, mobile access, and custom reporting to boost sales productivity."
        sample_requirements = ["Cloud-based CRM", "Sales and Marketing modules", "Accounting integration", "Mobile access", "Custom reporting"]
        sample_criteria = ["Ease of use", "Integration capabilities", "Cost"]
        sample_technology_generic = "A Custom Python-based CRM Solution"

        try:
            agent_generic = TechnicalWriterAgent(model_name="openai:gpt-3.5-turbo")
            print(f"TechnicalWriterAgent initialized for generic tech: {sample_technology_generic}")

            print("\n--- Generating Technical Content Set (Generic Tech) ---")
            technical_set_generic = await agent_generic.generate_all_technical_content(
                rfp_full_text=sample_rfp_text,
                rfp_summary=sample_summary,
                key_requirements=sample_requirements,
                evaluation_criteria=sample_criteria,
                chosen_technology=sample_technology_generic
            )
            print(f"Understanding: {technical_set_generic.understanding_requirements_content[:150]}...")
            print(f"Overview: {technical_set_generic.solution_overview_content[:150]}...")
            print(f"Architecture Text: {technical_set_generic.solution_architecture_descriptive_text[:150]}...")
            print(f"Mermaid Script:\n{technical_set_generic.solution_architecture_mermaid_script}")

            oem_product = "Salesforce Sales Cloud"
            print(f"\n--- Generating OEM Review for: {oem_product} ---")
            oem_review = await agent_generic.generate_oem_review(
                oem_product_name=oem_product,
                key_requirements=sample_requirements,
                rfp_summary=sample_summary
            )
            print(f"OEM Review Title: {oem_review.title}")
            print(f"OEM Review Content: {oem_review.content[:200]}...")

        except ValueError as ve:
            print(f"Input Error: {ve}")
        except Exception as e:
            import traceback
            print(f"An unexpected error occurred: {e}")
            print(traceback.format_exc())

    if __name__ == '__main__':
        asyncio.run(main_test())
