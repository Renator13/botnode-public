from pdf_reader_v1.models import PdfReaderInput, PdfReaderOutput


def test_input_output_models_validate_contract() -> None:
    payload = PdfReaderInput(file_url="https://example.com/paper.pdf", pages="1-2", extract_tables=False)
    output = PdfReaderOutput(page_count=2, metadata={"title": "Whitepaper"}, full_text="Some text")

    assert payload.file_url
    assert output.page_count == 2
