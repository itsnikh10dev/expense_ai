from prompt2 import build_category_prompt
import subprocess
import re

def get_category_from_ollama(description_text: str) -> str:
    prompt = build_category_prompt(description_text)

    # 2. Execute Ollama subprocess
    # Using Llama3 is recommended for better instruction following and JSON formatting.
    process = subprocess.Popen(
        ["ollama", "run", "qwen2.5:3b"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    output, error = process.communicate(input=prompt)

    if process.returncode != 0:
        return "Uncategorized LLM Error"

     # Clean the output: Remove quotes, backticks, and extra commentary
    cleaned_category = re.sub(r'["\'`]', '', output.strip(), flags=re.DOTALL).strip()
 
    
    # Ensure a category name is returned
    lines = cleaned_category.split('\n')
    final_category = lines[0].strip()
    
    if not final_category:
        return "Uncategorized - Empty Response"
        
    return final_category



description_text = "paying to cafe"
if __name__ == "__main__":
   category_list = get_category_from_ollama(description_text)
   print (category_list)