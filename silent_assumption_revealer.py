import json
import ollama
import sqlglot
from datetime import datetime
from pathlib import Path

from prompts import (
    SQL_GENERATION_PROMPT,
    ASSUMPTION_REVEAL_PROMPT
)

MODEL = "phi4:latest"


def load_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def call_ollama(prompt):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


def clean_response(text, identifier):
    text = text.strip()

    if text.startswith(f"```{identifier}"):
        text = text.replace(f"```{identifier}", "")
        text = text.replace("```", "")

    return text.strip()


def generate_sql(question, schema):
    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema,
        question=question
    )

    sql = call_ollama(prompt)

    return clean_response(sql, "sql")


def validate_sql(sql):
    try:
        parsed = sqlglot.parse_one(sql)
        return True, parsed
    except Exception as e:
        return False, str(e)


def reveal_assumptions(question, schema, sql):
    prompt = ASSUMPTION_REVEAL_PROMPT.format(
        schema=schema,
        question=question,
        sql=sql
    )

    response = call_ollama(prompt)

    response = clean_response(response, "json")

    try:
        return json.loads(response)
    except Exception:
        return {
            "error": "Failed to parse JSON",
            "raw_response": response
        }

def write_output(output):
    formatted_output = json.dumps(output, indent=2)

    print(formatted_output)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%d-%m-%Y--%H-%M-%S")
    file_path = output_dir / f"output-{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(formatted_output)

    print(f"\nSaved results to {file_path}")

def main():
    schema = load_schema("schema.txt")

    question = input("Enter natural language query:\n> ")

    print("\nGenerating SQL...\n")

    sql = generate_sql(question, schema)

    print("Generated SQL:\n")
    print(sql)

    valid, result = validate_sql(sql)

    if not valid:
        print("\nSQL validation failed:")
        print(result)
        return

    print("\nRevealing assumptions...\n")

    assumptions = reveal_assumptions(
        question,
        schema,
        sql
    )

    output = {
        "question": question,
        "sql": sql,
        "ambiguities": assumptions
    }

    write_output(output)


if __name__ == "__main__":
    main()