# BSc Thesis &ndash; Ambiguity in LLM-based NL2SQL System &ndash; Silent Assumption Revealer

## Setup

Download and Install [Ollama](https://ollama.com).

Current <model_name>: phi4:latest

Pull the model.
```
ollama pull <model_name>
```

Verify it works.
```
ollama run <model_name>
```

Install dependencies.
```
pip install -r requirements.txt
```

or alternatively:
```
py -m pip install -r requirements.txt
```

Open 2 terminals. <br>
In one run Ollama.
```
ollama serve
```

In the other run the program.
```
python .\silent_assumption_revealer.py
```

## Motivation
Every NL2SQL system must resolve ambiguity to produce a SQL query. When a natural language question is underspecified, the system makes an interpretive choice — it picks one reading and proceeds. The resulting SQL may be syntactically correct and executable, yet semantically wrong: it answers a question the user never asked.

The problem is not that systems make these choices. The problem is that they make them silently. The user sees a SQL query and a result, with no indication of which assumptions were made or what the query would have looked like under a different interpretation. This opacity makes it impossible for the user to detect misalignment, and difficult for researchers to study it systematically.

## Future Tasks

Be aware that currently I am using the first best model I found and that the schema is very small. Both the model and schema will and can change in the future. Additionally the prompts can change at any time.