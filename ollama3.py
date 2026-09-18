from prompt3 import user_query
import subprocess
import re

# Matches ANSI terminal control codes (cursor movement, "erase to end of
# line", color codes, etc.) that Ollama's CLI can print alongside its
# output when run as a subprocess. These must be stripped before the text
# is treated as SQL, or stray sequences like "\x1b[K" end up embedded in
# the query and break it.
_ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def response_to_user_query(user_input: str) -> str:
    prompt = user_query(user_input)
    process = subprocess.Popen(
        ["ollama", "run", "qwen2.5:3b"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    output, error = process.communicate(input=prompt)

    # Strip ANSI escape codes before any further cleaning happens.
    output = _ANSI_ESCAPE.sub("", output)

    # cleaning the output from llm  (ollama)

    if process.returncode != 0:
        raise RuntimeError(f"Ollama failed: {error}")

    # Remove triple backticks or SQL markdown blocks
    cleaned = re.sub(r"```.*?```", lambda m: m.group(0).strip("`"), output.strip(), flags=re.DOTALL)

    # Optional: remove remaining ` or ``` if present
    cleaned = cleaned.replace("```", "").strip("`").strip()

    # Split the string into lines
    lines = cleaned.split('\n')

    #  Check the first line for common language labels
    if lines and lines[0].strip().lower() in ['sql', 'sqlite', 'markdown']:
        lines = lines[1:]  # Remove the first line

    #  Join the lines back together
    cleaned = '\n'.join(lines).strip()

    return cleaned