import fitz


def extract_text_from_pdf(uploaded_file):

    pdf_bytes = uploaded_file.getvalue()

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page in document:

        text = page.get_text()

        if text:
            pages.append(text)

    document.close()

    return "\n".join(pages)