import os
from typing import Union, List
from PyPDF2 import PdfReader
from markdown_it import MarkdownIt
from ..models.rfp_models import RFP, RFPSection # Assuming rfp_models.py is one level up in models directory

class RFPParser:
    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file {file_path} was not found.")
        self.file_path = file_path
        self.file_type = self._get_file_type()

    def _get_file_type(self) -> str:
        _, file_extension = os.path.splitext(self.file_path)
        if file_extension.lower() == '.pdf':
            return 'pdf'
        elif file_extension.lower() in ['.md', '.markdown']:
            return 'markdown'
        else:
            raise ValueError("Unsupported file type. Only PDF and Markdown files are supported.")

    def _parse_pdf(self) -> str:
        text_content = []
        try:
            with open(self.file_path, 'rb') as f:
                reader = PdfReader(f)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text_content.append(page.extract_text() or "")
            return "\n".join(text_content)
        except Exception as e:
            print(f"Error reading PDF file: {e}")
            return "" # Return empty string or raise a custom exception

    def _parse_markdown(self) -> str:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            # For now, just return the raw markdown text.
            # Parsing into HTML or a token stream can be done if needed for structuring.
            # md = MarkdownIt()
            # html_content = md.render(md_content)
            return md_content
        except Exception as e:
            print(f"Error reading Markdown file: {e}")
            return "" # Return empty string or raise a custom exception

    def parse(self) -> RFP:
        '''
        Parses the RFP file and returns an RFP object.
        Currently, it extracts the full text and places it into a single RFPSection.
        Further refinement can be done to split into more meaningful sections.
        '''
        full_text = ""
        if self.file_type == 'pdf':
            full_text = self._parse_pdf()
        elif self.file_type == 'markdown':
            full_text = self._parse_markdown()

        # Basic sectioning: treat the whole document as one section for now.
        # This can be improved later with more sophisticated section detection logic
        # or by leveraging an AI agent.
        initial_section = RFPSection(title="Full Document", content=full_text)

        return RFP(
            file_name=os.path.basename(self.file_path),
            full_text=full_text,
            sections=[initial_section]
            # summary, key_requirements, evaluation_criteria will be filled by AI agents later
        )

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Create dummy files for testing
    if not os.path.exists("dummy.pdf"):
        # This is tricky to do without a library that creates PDFs or a real dummy PDF.
        # For now, this part of the example will only work if a dummy.pdf exists.
        # Consider adding a small, simple PDF to your examples/rfps directory for testing.
        print("Please create a dummy.pdf for testing the PDF parser.")

    if not os.path.exists("dummy.md"):
        with open("dummy.md", "w") as f:
            f.write("# Test Markdown\nThis is a test.")

    # Test Markdown
    if os.path.exists("dummy.md"):
        md_parser = RFPParser("dummy.md")
        parsed_md_rfp = md_parser.parse()
        print(f"--- Parsed Markdown ({parsed_md_rfp.file_name}) ---")
        # print(f"Full Text: {parsed_md_rfp.full_text[:200]}...") # Print first 200 chars
        if parsed_md_rfp.sections:
             print(f"First Section Content: {parsed_md_rfp.sections[0].content}")
        # print(f"Summary: {parsed_md_rfp.summary}")


    # Test PDF (requires a dummy.pdf file)
    if os.path.exists("dummy.pdf"):
        pdf_parser = RFPParser("dummy.pdf")
        parsed_pdf_rfp = pdf_parser.parse()
        print(f"--- Parsed PDF ({parsed_pdf_rfp.file_name}) ---")
        # print(f"Full Text: {parsed_pdf_rfp.full_text[:200]}...")
        if parsed_pdf_rfp.sections:
            print(f"First Section Content (PDF): {parsed_pdf_rfp.sections[0].content[:200]}...")
        # print(f"Summary: {parsed_pdf_rfp.summary}")

    # Clean up dummy files
    # if os.path.exists("dummy.md"):
    #     os.remove("dummy.md")
    # if os.path.exists("dummy.pdf"):
    #     pass # Cannot remove dummy.pdf if it was manually created
