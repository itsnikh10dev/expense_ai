import json

# Define the precise schema for the extracted invoice data

JSON_SCHEMA = {
    "Invoice_No": "The unique invoice identifier.",
    "Issue_Date": "The date the invoice was created (format: MM/DD/YYYY)",
    "billed_to": "Name of the company / person to whom bill is charged.",
    "billed_by": "Name of company who has issued the bill.",
    "Description": "A list of individual service descriptions",
    "Amount": "A list of bill amounts for each individual service (must be numbers).",
    "Grand_Total": "The total amount in the bill (must be a single number, float or integer)."
}

def data_conversion(extracted_text: str) -> str:
    schema_string = json.dumps(JSON_SCHEMA, indent=2)
    return f"""
You are an expert in the data extraction bot. Your sole task is to analyse the raw data from the OCR text from a single invoice and convert it into a valid JSON object based on the required schema

# Required JSON SCHEMA
{schema_string}

# Extraction
- **STRICTLY: ** Return only valid JSON Object 


---
Raw Invoice text to analyze:
{extracted_text}

Return only valid JSON Object

---


"""