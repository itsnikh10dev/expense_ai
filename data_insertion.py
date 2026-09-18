import sqlite3
import os
from parser import parse_multiple_invoices

DB_NAME = "ocr_master.db"
TABLE_NAME = "ocr_line_items"

def insert_extracted_data():
    con = None
    insert_count = 0

    try:
        #connecting with database 
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()

        all_bill_data = parse_multiple_invoices()


        if not all_bill_data:
            print("no data")
            return
        print (f"data to be extracted, {len(all_bill_data)}")

        #looping through each bill data
        for bill_dict in all_bill_data:
            encriched_line_items = bill_dict.get('Description',[])

            #looping for each line items for invoice number, date, .....
            for i, item_dict in enumerate(encriched_line_items):
                if not isinstance(item_dict, dict):
                    print(f"skipping line items for invoice number{bill_dict.get('Invoice_No')}")
                    return
                
                #fetching information and storing it : 
                data_tuple = (
                    bill_dict.get('Invoice_No'),
                    i+1,
                    bill_dict.get('Issue_Date'),
                    bill_dict.get('billed_to'),
                    bill_dict.get('billed_by'),
                    item_dict.get('service_description'), # Extracted from the dictionary
                    item_dict.get('Category'),            # <-- NEW CATEGORY DATA
                    item_dict.get('Amount'),              # Extracted from the dictionary
                    bill_dict.get('Grand_Total'),
                    bill_dict.get('source_file')
                )

                #uploading the data into table 
                cur.execute(f"""
                            INSERT OR REPLACE INTO {TABLE_NAME}
                            (Invoice_No, line_item_id, Issue_Date, billed_to, billed_by, Description, Category, Amount, Grand_Total, source_file)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, data_tuple)
                insert_count += 1
        
        con.commit()
        print(f"data insertion for {insert_count} completed")

    except sqlite3.Error as e:
        print(f"❌ SQLite Error: {e}")
        # Note: Combining multiple except blocks like your original code is invalid Python syntax.
        # This structure handles the SQL error.
    
    except Exception as e:
         print(f"❌ General Error during insertion: {e}")

    finally:
        if con:
            con.close()


if __name__ == "__main__":
    insert_extracted_data()
                




