from ..models.proposal_models import Proposal, UnderstandingRequirements, SolutionOverview, SolutionArchitecture, OEMSolutionReview
from typing import List, Optional, Union

class FormattingAgent:
    def __init__(self):
        pass # No LLM needed for this agent

    def format_proposal_to_markdown(self, proposal_data: Proposal) -> str:
        '''
        Formats the new technically-focused Proposal object into a Markdown string.
        '''
        markdown_output = []

        # Helper to append section content if it exists and is not empty
        def append_text_content(title: str, content: Optional[str], level: int = 1):
            if content and content.strip():
                markdown_output.append(f"{'#' * level} {title}\n")
                markdown_output.append(f"{content.strip()}\n")

        # RFP Reference and Target Technology (as metadata or preamble)
        if proposal_data.rfp_reference_document:
            markdown_output.append(f"**Based on RFP:** {proposal_data.rfp_reference_document}\n")
        markdown_output.append(f"**Proposed Technology Focus:** {proposal_data.target_technology}\n")
        markdown_output.append("---\n") # Separator

        # 1. Understanding of Requirements
        if proposal_data.understanding_requirements:
            append_text_content(
                proposal_data.understanding_requirements.title,
                proposal_data.understanding_requirements.content,
                level=1
            )

        # 2. Solution Overview
        if proposal_data.solution_overview:
            append_text_content(
                proposal_data.solution_overview.title,
                proposal_data.solution_overview.content,
                level=1
            )

        # 3. Solution Architecture
        if proposal_data.solution_architecture:
            arch_section = proposal_data.solution_architecture
            # Append descriptive text first
            append_text_content(
                arch_section.title, # This title is "Solution Architecture"
                arch_section.descriptive_text,
                level=1
            )
            # Then append Mermaid script if it exists
            if arch_section.mermaid_script and arch_section.mermaid_script.strip():
                # Ensure the mermaid script from LLM is correctly wrapped.
                # LLM was prompted to include ```mermaid ... ```, but we can double check.
                mermaid_content = arch_section.mermaid_script.strip()
                if not mermaid_content.startswith("```mermaid"):
                    mermaid_content = "```mermaid\n" + mermaid_content
                if not mermaid_content.endswith("```"):
                    mermaid_content = mermaid_content + "\n```"

                markdown_output.append(f"\n**Reference Architecture Diagram:**\n") # Sub-heading for the diagram
                markdown_output.append(f"{mermaid_content}\n")

        # 4. OEM Solution Reviews (if any)
        if proposal_data.oem_solution_reviews:
            for review in proposal_data.oem_solution_reviews:
                if review and review.content and review.content.strip():
                    # The title for OEMSolutionReview is set by the agent to be specific
                    append_text_content(
                        review.title, # e.g., "Overview: OutSystems"
                        review.content,
                        level=2 # Typically a sub-section
                    )

        return "\n".join(markdown_output)

if __name__ == '__main__':
    # Example Usage
    print("Testing FormattingAgent (Revised)...")

    # Create dummy proposal data based on new models
    understanding = UnderstandingRequirements(content="Client requires X, Y, Z. Our understanding is...")
    overview = SolutionOverview(content="We propose a solution based on microservices...")
    architecture = SolutionArchitecture(
        descriptive_text="The architecture has three layers...",
        mermaid_script="```mermaid\ngraph TD;\nA-->B;\nB-->C;\n```"
    )
    oem_review1 = OEMSolutionReview(
        oem_product_name="MegaPlatform X",
        title="Overview: MegaPlatform X", # Agent is expected to set this
        content="MegaPlatform X is a leading solution for..."
    )
    oem_review2 = OEMSolutionReview(
        oem_product_name="WidgetSuite Pro",
        title="Overview: WidgetSuite Pro",
        content="WidgetSuite Pro offers advanced widget capabilities..."
    )

    full_proposal = Proposal(
        rfp_reference_document="RFP_TechFocus_2024.pdf",
        target_technology="Cloud-Native Microservices with Kubernetes",
        understanding_requirements=understanding,
        solution_overview=overview,
        solution_architecture=architecture,
        oem_solution_reviews=[oem_review1, oem_review2]
    )

    formatter = FormattingAgent()
    markdown_result = formatter.format_proposal_to_markdown(full_proposal)

    print("\n--- Generated Markdown Proposal (Revised) ---")
    print(markdown_result)

    # Test with some missing parts (e.g., no OEM reviews)
    minimal_proposal = Proposal(
        target_technology="Simple Web App",
        understanding_requirements=UnderstandingRequirements(content="Client needs a basic website."),
        solution_overview=SolutionOverview(content="A static site generated with Hugo."),
        solution_architecture=SolutionArchitecture(descriptive_text="No complex architecture needed.", mermaid_script=None)
        # oem_solution_reviews is None by default
    )
    markdown_minimal = formatter.format_proposal_to_markdown(minimal_proposal)
    print("\n--- Generated Minimal Markdown Proposal (Revised) ---")
    print(markdown_minimal)

    # Test with mermaid script needing wrapping
    architecture_needs_wrap = SolutionArchitecture(
        descriptive_text="Architecture with unwrapped Mermaid.",
        mermaid_script="graph TD;\n  Start --> End;"
    )
    proposal_mermaid_wrap = Proposal(
        target_technology="Test Wrap",
        understanding_requirements=understanding, # reuse
        solution_overview=overview, # reuse
        solution_architecture=architecture_needs_wrap
    )
    markdown_wrapped = formatter.format_proposal_to_markdown(proposal_mermaid_wrap)
    print("\n--- Generated Proposal with Mermaid Wrapping ---")
    print(markdown_wrapped)
