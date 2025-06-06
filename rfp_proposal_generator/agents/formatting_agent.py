from ..models.proposal_models import Proposal, ProposalSection, Introduction, ExecutiveSummary, TechnicalSolution, TeamQualifications, Pricing
from typing import List, Optional, Union

class FormattingAgent:
    def __init__(self):
        # This agent might not need an LLM initially,
        # but one could be added later for text refinement or advanced formatting.
        pass

    def format_proposal_to_markdown(self, proposal_data: Proposal) -> str:
        '''
        Formats the Proposal object into a Markdown string.
        It iterates through the known sections and any custom sections.
        '''
        markdown_output = []

        # Helper to append section if it exists and has content
        def append_section(section: Optional[ProposalSection], level: int = 1):
            if section and section.content and section.content.strip():
                markdown_output.append(f"{'#' * level} {section.title}\n")
                markdown_output.append(f"{section.content.strip()}\n")

        # RFP Reference and Target Technology (as metadata or preamble)
        if proposal_data.rfp_reference_document:
            markdown_output.append(f"**Based on RFP:** {proposal_data.rfp_reference_document}\n")
        markdown_output.append(f"**Proposed Technology Focus:** {proposal_data.target_technology}\n")
        markdown_output.append("---\n") # Separator

        # Standard Sections in a specific order
        if proposal_data.introduction:
            append_section(proposal_data.introduction, level=1)

        if proposal_data.executive_summary:
            append_section(proposal_data.executive_summary, level=1)

        # Technical Solution is mandatory in the model, but check content
        if proposal_data.technical_solution and proposal_data.technical_solution.content.strip():
            append_section(proposal_data.technical_solution, level=1)

        if proposal_data.team_qualifications:
            append_section(proposal_data.team_qualifications, level=2) # Example of different heading level

        if proposal_data.pricing:
            append_section(proposal_data.pricing, level=2)

        # Handle other_sections if they are used (not currently in Proposal model, but good for future)
        # if hasattr(proposal_data, 'other_sections') and proposal_data.other_sections:
        #     for section in proposal_data.other_sections:
        #         append_section(section, level=2)

        return "\n".join(markdown_output)

if __name__ == '__main__':
    # Example Usage
    print("Testing FormattingAgent...")

    # Create dummy proposal data
    intro = Introduction(content="This is the introduction to our amazing proposal.")
    exec_sum = ExecutiveSummary(content="We propose to do X, Y, and Z with great success.")
    tech_sol = TechnicalSolution(
        # title is set by default in the model
        content="Our technical solution involves advanced algorithms and cloud infrastructure. We will use Python and Kubernetes."
    )
    team_q = TeamQualifications(content="Our team is highly experienced in relevant fields.")
    price_info = Pricing(content="Pricing is competitive. Tier 1: $100, Tier 2: $200.")

    full_proposal = Proposal(
        rfp_reference_document="RFP_XYZ_2024.pdf",
        target_technology="AI and Machine Learning",
        introduction=intro,
        executive_summary=exec_sum,
        technical_solution=tech_sol,
        team_qualifications=team_q,
        pricing=price_info
    )

    formatter = FormattingAgent()
    markdown_result = formatter.format_proposal_to_markdown(full_proposal)

    print("\n--- Generated Markdown Proposal ---")
    print(markdown_result)

    # Test with some missing sections
    partial_proposal = Proposal(
        target_technology="React Native",
        technical_solution=TechnicalSolution(content="We will build a mobile app using React Native.")
    )
    markdown_partial = formatter.format_proposal_to_markdown(partial_proposal)
    print("\n--- Generated Partial Markdown Proposal ---")
    print(markdown_partial)
