import pytest
import os
from rfp_proposal_generator.parsers.rfp_parser import RFPParser
from rfp_proposal_generator.models.rfp_models import RFP

# Create dummy files in the examples/rfps directory for testing
EXAMPLES_DIR = "examples/rfps"
DUMMY_MD_FILE = os.path.join(EXAMPLES_DIR, "test_dummy.md")
DUMMY_PDF_FILE = os.path.join(EXAMPLES_DIR, "test_dummy.pdf") # Actual PDF content not needed for all tests

@pytest.fixture(scope="module", autouse=True)
def create_dummy_files():
    os.makedirs(EXAMPLES_DIR, exist_ok=True)
    with open(DUMMY_MD_FILE, "w") as f:
        f.write("# Test RFP\nThis is a test markdown file for RFP parsing.")
    # Create an empty dummy PDF file if it doesn't exist.
    # The parser should handle it (e.g. by extracting no text or raising specific error if library expects valid PDF)
    if not os.path.exists(DUMMY_PDF_FILE):
        open(DUMMY_PDF_FILE, 'a').close()

    yield

    # Teardown: remove dummy files after tests
    # if os.path.exists(DUMMY_MD_FILE):
    #     os.remove(DUMMY_MD_FILE)
    # if os.path.exists(DUMMY_PDF_FILE):
    #     os.remove(DUMMY_PDF_FILE) # Be cautious if you have a real sample PDF there

def test_unsupported_file_type():
    with open("unsupported.txt", "w") as f:
        f.write("test")
    with pytest.raises(ValueError, match="Unsupported file type"):
        RFPParser("unsupported.txt")
    os.remove("unsupported.txt")

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        RFPParser("non_existent_file.pdf")

def test_parse_markdown_file():
    parser = RFPParser(DUMMY_MD_FILE)
    rfp_data = parser.parse()
    assert isinstance(rfp_data, RFP)
    assert rfp_data.file_name == "test_dummy.md"
    assert "# Test RFP" in rfp_data.full_text
    assert len(rfp_data.sections) == 1
    assert rfp_data.sections[0].title == "Full Document"
    assert "# Test RFP" in rfp_data.sections[0].content

def test_parse_pdf_file_empty():
    # This test assumes an empty or non-PDF content file will result in empty text extraction
    # PyPDF2 might raise an error for a truly empty or malformed PDF.
    # For this test, an empty file is used.
    # If PyPDF2 raises an error on empty files, this test needs adjustment
    # or a tiny valid PDF.
    parser = RFPParser(DUMMY_PDF_FILE)
    rfp_data = parser.parse()
    assert isinstance(rfp_data, RFP)
    assert rfp_data.file_name == "test_dummy.pdf"
    # Depending on PyPDF2's behavior with empty/invalid PDFs, full_text might be empty or raise an error during parse
    # For now, let's assume it extracts empty text without error for a 0-byte file.
    assert rfp_data.full_text == ""
    assert len(rfp_data.sections) == 1
    assert rfp_data.sections[0].content == ""

# To test PDF text extraction properly, a small, valid PDF file would be needed in 'examples/rfps/'
# For example, 'examples/rfps/real_sample.pdf'
# @pytest.mark.skipif(not os.path.exists(os.path.join(EXAMPLES_DIR, "real_sample.pdf")), reason="Requires a real sample PDF file")
# def test_parse_real_pdf_file():
#     parser = RFPParser(os.path.join(EXAMPLES_DIR, "real_sample.pdf"))
#     rfp_data = parser.parse()
#     assert isinstance(rfp_data, RFP)
#     assert rfp_data.file_name == "real_sample.pdf"
#     assert len(rfp_data.full_text) > 0 # Assuming real PDF has text
#     assert len(rfp_data.sections) == 1
#     assert len(rfp_data.sections[0].content) > 0
