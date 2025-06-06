import os
from typing import Optional, List # Added List

from .parsers.rfp_parser import RFPParser
from .agents.rfp_reviewer_agent import RFPReviewerAgent # Stays the same
from .agents.technical_writer_agent import TechnicalWriterAgent, TechnicalContentSet # TechnicalWriterAgent is revised
from .agents.formatting_agent import FormattingAgent # FormattingAgent is revised
from .models.rfp_models import RFP
# Import new proposal models
from .models.proposal_models import (
    Proposal, UnderstandingRequirements, SolutionOverview,
    SolutionArchitecture, OEMSolutionReview
)

class ProposalGenerator:
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

    def _is_oem_technology(self, technology_name: str) -> bool:
        oem_keywords = ["salesforce", "outsystems", "sap", "oracle", "microsoft dynamics", "servicenow", "workday"]
        technology_name_lower = technology_name.lower()
        for keyword in oem_keywords:
            if keyword in technology_name_lower:
                return True
        return False

    async def generate_proposal(self, rfp_file_path: str, target_technology: str) -> str:
        print(f"Starting technical proposal generation for RFP: {rfp_file_path} using technology: {target_technology}")

        print("Step 1: Parsing RFP...")
        self.rfp_parser = RFPParser(file_path=rfp_file_path)
        parsed_rfp_doc: RFP = self.rfp_parser.parse()
        if not parsed_rfp_doc.full_text or not parsed_rfp_doc.full_text.strip():
            raise ValueError(f"Failed to parse content from RFP file: {rfp_file_path}. Full text is empty.")
        print(f"RFP parsed. Extracted text length: {len(parsed_rfp_doc.full_text)}")

        print("Step 2: Reviewing RFP with RFPReviewerAgent...")
        reviewed_rfp_doc = await self.rfp_reviewer_agent.review_rfp(parsed_rfp_doc)
        if not reviewed_rfp_doc.summary and not reviewed_rfp_doc.key_requirements:
             print("Warning: RFP review did not yield a summary or key requirements. Quality may be affected.")
        else:
            print(f"RFP review complete. Summary (first 100 chars): {reviewed_rfp_doc.summary[:100] if reviewed_rfp_doc.summary else 'N/A'}...")
            print(f"Key Requirements (first 2): {reviewed_rfp_doc.key_requirements[:2] if reviewed_rfp_doc.key_requirements else 'N/A'}...")

        print("Step 3: Generating core technical content with TechnicalWriterAgent...")
        technical_content_set: TechnicalContentSet = await self.technical_writer_agent.generate_all_technical_content(
            rfp_full_text=parsed_rfp_doc.full_text,
            rfp_summary=reviewed_rfp_doc.summary,
            key_requirements=reviewed_rfp_doc.key_requirements or [], # Ensure it's a list
            evaluation_criteria=reviewed_rfp_doc.evaluation_criteria,
            chosen_technology=target_technology
        )
        print("Core technical content generated.")

        oem_reviews_list: Optional[List[OEMSolutionReview]] = None
        if self._is_oem_technology(target_technology):
            print(f"Step 4a: Generating OEM review for {target_technology}...")
            oem_review = await self.technical_writer_agent.generate_oem_review(
                oem_product_name=target_technology,
                key_requirements=reviewed_rfp_doc.key_requirements,
                rfp_summary=reviewed_rfp_doc.summary
            )
            oem_reviews_list = [oem_review]
            print(f"OEM review for {target_technology} generated.")
        else:
            print("Step 4a: No specific OEM review triggered by target technology name.")

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
