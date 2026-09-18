import pytesseract
import os

# # set the path to the Tesseract exectable (required since its not on the syatem path)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

INPUT_FOLDER = "image_cleaning_one_folder"
OUTPUT_FILE = "extracted_text.txt"


def perform_ocr(INPUT_FOLDER, OUTPUT_FILE):
    all_extracted_text = ""
    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith((".jpeg", ".jpg", ".png")):
            image_path = os.path.join(INPUT_FOLDER, filename)
            try:
                text = pytesseract.image_to_string(image_path)
                print("-"*20)
                print(text.strip)
                print("-"*20)
                all_extracted_text += f"\n-- Text from {filename}--\n{text}\n"
            except Exception as e:
                print(f"error in {filename}: {e}")


    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(all_extracted_text)  

        print(f"Complete ocr done")

if __name__ == "__main__":
    perform_ocr(INPUT_FOLDER, OUTPUT_FILE)