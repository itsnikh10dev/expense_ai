# Category buckets

CATEGORIES = [
    "food", "logistic", "drinks", "travel", "Grocery expense", "Utilities", "Other"
]

def build_category_prompt(description_text:str) -> str:
    category_list = ",".join(CATEGORIES)
    return f"""
you are an expert classification agent. Your task is to analyze the following single service description and assign it to one of predefined category.

predefined categories:
{category_list}

#Instructions: 
- **STRICTLY** return ONLY the chosen category name as a single string. 
- If the description is vague or doesn't fit, choose "Other".
- The output MUST match one of the categories exactly.
- DO NOT return any quotes, explanation, or markdown.

---
Service Description to categorize : "{description_text}"

"""