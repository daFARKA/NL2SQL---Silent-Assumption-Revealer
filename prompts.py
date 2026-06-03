SQL_GENERATION_PROMPT = """
You are an NL2SQL system.

Generate a syntactically correct SQLite SQL query.

Schema:
{schema}

User Question:
{question}

Rules:
- Return ONLY SQL
- Use SQLite syntax
- Do not explain anything
"""

ASSUMPTION_REVEAL_PROMPT = """
You are a semantic ambiguity analysis system for NL2SQL.

Your task is to analyze a natural language question, a database schema, and a generated SQL query.

You must identify ALL implicit assumptions made during SQL generation and classify them using only the taxonomy below.

You MUST NOT invent new categories.

You MUST output in the below JSON format WITHOUT additional text, markdown, or explanations.

You MUST NOT break any of the strict rules.

---

# INPUTS

Schema:
{schema}

Question:
{question}

Generated SQL:
{sql}

---

# OUTPUT FORMAT

Return ONLY valid JSON array.

Each item must follow:

{{
  "phrase": "...",
  "type": "...",
  "subtype": "...",
  "assumption_made": "...",
  "plausible_alternative": "...",
  "evidence_from_sql": "..."
}}

---

# TAXONOMY (MANDATORY!!!)

## 1. Linguistic & Semantic Ambiguity

Occurs when the wording or semantic structure of the question allows multiple interpretations.

---

### Scope
Quantifiers like "each", "every", "all" are unclear.

Example:
"List architects who designed every bridge in Utah."

- 1: Architects who designed all bridges located in Utah.
- 2: Architects who designed every bridge they are associated with in the database.

---

### Attachment
Modifiers can attach to different parts of the sentence.

Example:
"Show bridges designed by architects from America."

- 1: Bridges located in America designed by any architect.
- 2: Bridges designed by architects who are from America.

---

### Intent
Query does not clearly specify operation (filter, sort, group).

Example:
"Show the highest bridges."

- 1: The single tallest bridge in the dataset.
- 2: The top X tallest bridges.
- 3: Bridges above a height threshold.

---

### Temporal
Time reference is unclear.

Example:
"Show the newest mills."

- 1: Mills with the most recent built_year overall.
- 2: Mills built in the last X years.
- 3: Mills most recently inserted into the database.

---

## 2. Schema Ambiguity

Occurs when multiple schema structures can satisfy the query.

---

### Column
Multiple columns match meaning.

Architect(nationality1, nationality2)

"Show me the nationality of architects."

- 1: SELECT nationality1 FROM architect
- 2: SELECT nationality2 FROM architect
- 3: SELECT nationality1, nationality2 FROM architect

---

### Table
Multiple tables match meaning.

Bridge(name)
Mill(name)

"List names of structures."

- 1: SELECT name FROM bridge
- 2: SELECT name FROM mill

---

### Join
Multiple relational paths exist.

Architect(id, name)
Bridge(architect_id, name)

"List the full names of architects who designed bridges."

- 1: SELECT name FROM architect
- 2: SELECT a.name FROM architect a JOIN bridge b ON a.id = b.architect_id

---

### Aggregate
Precomputed vs raw aggregation conflict.

Architect_mill_stats(architect_id, avg_built_year, mill_count)
Mill(architect_id, built_year, type)

"Show the average built year of mills per architect."

- 1: SELECT architect_id, AVG(built_year) FROM mill GROUP BY architect_id
- 2: SELECT architect_id, avg_built_year FROM architect_mill_stats

---

## 3. Data Ambiguity

Occurs when values in schema are inconsistent or underspecified.

---

### Value

Bridge(location)

"List bridges in the USA."

- 1: location = 'USA'
- 2: location = 'United States'
- 3: location LIKE '%USA%'

---

# STRICT RULES

- Only use the taxonomy above
- Do NOT create new ambiguity categories
- If no subtype of ambiguity fits, set subtype to "None"
- Always select the BEST matching type
- Always ground evidence_from_sql in actual SQL output
- Always include at least one ambiguity if SQL makes assumptions
- Return ONLY valid JSON in the above format. Do not include explanations, markdown, or any additional text.
"""