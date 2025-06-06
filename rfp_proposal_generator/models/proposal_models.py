from pydantic import BaseModel, Field
from typing import List, Optional

class ProposalSection(BaseModel):
    title: str = Field(description="Title of this proposal section")
    content: str = Field(description="Generated content for this proposal section")

class Introduction(ProposalSection):
    title: str = "Introduction"
    # client_name: Optional[str] = Field(default=None, description="Name of the client or organization that issued the RFP")
    # project_understanding: str = Field(description="Our understanding of the project/problem")

class ExecutiveSummary(ProposalSection):
    title: str = "Executive Summary"
    # key_points: List[str] = Field(description="Key points summarizing the proposal")

class TechnicalSolution(ProposalSection):
    title: str = "Technical Solution"
    # proposed_technology: str = Field(description="The core technology proposed for the solution")
    # architecture_description: Optional[str] = Field(default=None, description="Description of the proposed system architecture")
    # implementation_plan: Optional[str] = Field(default=None, description="High-level plan for implementation")

class TeamQualifications(ProposalSection):
    title: str = "Team Qualifications"
    # team_overview: str = Field(description="Overview of the team's expertise")
    # relevant_experience: Optional[List[str]] = Field(default=None, description="Examples of relevant past projects or experience")

class Pricing(ProposalSection):
    title: str = "Pricing"
    # pricing_details: str = Field(description="Details of the pricing structure") # Could be a table or structured text

class Proposal(BaseModel):
    rfp_reference_document: Optional[str] = Field(default=None, description="Reference to the original RFP document")
    target_technology: str = Field(description="The technology the proposal is based on")
    introduction: Optional[Introduction] = Field(default=None)
    executive_summary: Optional[ExecutiveSummary] = Field(default=None)
    technical_solution: TechnicalSolution
    team_qualifications: Optional[TeamQualifications] = Field(default=None)
    pricing: Optional[Pricing] = Field(default=None)
    # other_sections: List[ProposalSection] = Field(default_factory=list, description="Any other custom sections")
