import os 
import json
from ollama1 import get_json_from_prompt
from ollama2 import get_category_from_ollama

OCR_OUTPUT_FILE = "extracted_text.txt"

def parse_multiple_invoices():
    print(f"Parsing started...")

    if not os.path.exists(OCR_OUTPUT_FILE):
        print(f"OCR file not found at {OCR_OUTPUT_FILE}")
        return []
    
    with open(OCR_OUTPUT_FILE, 'r', encoding='utf8') as f:
        master_text = f.read()

    # Split using the marker you chose
    bill_section = master_text.split("-- Text from ")[1:]
    total_bills = len(bill_section)
    print(f"Total bills to process: {total_bills}")

    all_structured_list = []

    for section in bill_section:
        try:
            # Splitting filename and content
            filename = section.split("--")[0].strip()
            bill_text = section.split("--", 1)[1].strip()
            print(f"\n🧠 Processing: {filename}")

            # Agent 1: Extraction
            structured_data_dict = get_json_from_prompt(bill_text)
            
            #breaking multiple descriptions into single line item id
            if structured_data_dict:
                description_list = structured_data_dict.get('Description', [])
                amount_list = structured_data_dict.get('Amount', [])
                enriched_descriptions = []

                # Agent 2: Categorization (Indented correctly now!)
                for desc_item_raw, amt in zip(description_list, amount_list):
                    #converting into string as AI understand this only
                    service_name = str(desc_item_raw).strip()
                    print(f"   > Categorizing: {service_name}")
                    
                    category_label = get_category_from_ollama(service_name)

                    enriched_item = {
                        'service_description': service_name,
                        'Amount': amt,
                        'Category': category_label
                    }
                    enriched_descriptions.append(enriched_item)

                # Update the main dict with the enriched list
                structured_data_dict['Description'] = enriched_descriptions
                structured_data_dict['source_file'] = filename
                
                all_structured_list.append(structured_data_dict)
            else:
                print(f"Failed to extract data for {filename}")
        
        except Exception as e:
            print(f"Error processing section: {e}")

    return all_structured_list


if __name__ == "__main__":
    final_extracted_data = parse_multiple_invoices()
    print("\nFinal List of Bills Generated!")
    # Use json.dumps for pretty printing the final result
    print(json.dumps(final_extracted_data, indent=4))







