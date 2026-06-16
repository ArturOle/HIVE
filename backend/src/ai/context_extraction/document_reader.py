from docling.document_converter import DocumentConverter


def read_document(file_path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(source=file_path)
    markdown_content = result.document.export_to_markdown()
    return markdown_content


if __name__ == "__main__":
    # Example usage
    content = read_document("/home/r2/Documents/Projects/ReLived/backend/data_cold/eu_gdpr.txt")  # Replace with your document path
    print(content)