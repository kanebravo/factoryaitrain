from pydantic import BaseModel, Field
from typing import List, Optional

class RFPSection(BaseModel):
    title: Optional[str] = Field(default=None, description="Title of the RFP section")
    content: str = Field(description="Text content of the RFP section")
    sub_sections: Optional[List['RFPSection']] = Field(default=None, description="Nested sub-sections, if any")

class RFP(BaseModel):
    file_name: Optional[str] = Field(default=None, description="Original filename of the RFP")
    full_text: Optional[str] = Field(default=None, description="Entire text content of the RFP")
    text_chunks: Optional[List[str]] = Field(default=None, description="Full text broken into manageable chunks for LLM processing")
    sections: List[RFPSection] = Field(description="List of identified sections in the RFP")
    summary: Optional[str] = Field(default=None, description="AI-generated summary of the RFP")
    key_requirements: Optional[List[str]] = Field(default=None, description="List of key requirements extracted from the RFP")
    evaluation_criteria: Optional[List[str]] = Field(default=None, description="List of evaluation criteria mentioned in the RFP")
