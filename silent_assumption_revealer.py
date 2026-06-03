import json
import ollama
import sqlglot
import argparse
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

from prompts import (
    SQL_GENERATION_PROMPT,
    ASSUMPTION_REVEAL_PROMPT
)

MODEL = "phi4:latest"

def parse_args_input_path():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Path to the input JSON file containing queries")

    args = parser.parse_args()
    input_path = args.input

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("Input file not found")
    except json.JSONDecodeError:
        raise ValueError("Input file is not valid JSON")

    return input_path

def load_schema(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_queries(path):
    with open(path, "r", encoding="utf-8") as f:
        queries = json.load(f)
    
    return queries

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

    last_idx = text.rfind("]")
    if last_idx == -1:
        return text.strip()
    
    return text[:last_idx + 1].strip()


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

def write_output(outputs, timestamp):
    formatted_output = json.dumps(outputs, indent=2, ensure_ascii=False)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{timestamp}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(formatted_output)

    print(f"Saved results to {file_path}")

def main():
    input_path = parse_args_input_path()

    schema = load_schema("schema_architecture_adapted.sql")

    queries = load_queries(input_path)

    outputs = []
    for question in tqdm(queries, desc="Processing NL queries", unit="query"):
        sql = generate_sql(question['query'], schema)

        valid, result = validate_sql(sql)

        if not valid:
            tqdm.write(f"SQL validation failed for ID: {question['id']}")
            tqdm.write(result)

        assumptions = reveal_assumptions(
            question['query'],
            schema,
            sql
        )

        output = {
            "id": question['id'],
            "question": question['query'],
            "sql": sql,
            "ambiguities": assumptions,
            "expected_ambiguities": question['expected_ambiguities'],
            "validation": {
                "valid": valid,
                "error": result if not valid else None
            }
        }

        outputs.append(output)
    
    write_output(outputs, datetime.now().strftime("%d-%m-%Y--%H-%M-%S"))

    return


if __name__ == "__main__":
    main()