from src.pdf_extractor import extract_text_from_pdf
from src.patient_parser import parse_patient


with open(
    "test_patient.pdf",
    "rb"
) as f:

    text = f.read()


class FakeUpload:

    def getvalue(self):
        return text


raw_text = extract_text_from_pdf(
    FakeUpload()
)


print("\n========== EXTRACTED PATIENT ==========\n")

patient = parse_patient(
    raw_text
)

print(patient)