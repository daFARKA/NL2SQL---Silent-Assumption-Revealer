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

You must identify ALL implicit assumptions made during SQL generation and classify them using the taxonomy below.

You MUST NOT invent new categories.

You MUST NOT break any of the strict rules.

---

# INPUTS

SCHEMA:
{schema}

QUESTION:
{question}

GENERATED SQL:
{sql}

---

# OUTPUT FORMAT

Return ONLY valid JSON array.

Each item must follow:

{{
  "ambiguous_phrase": "...",
  "ambiguity_type": "...",
  "subtype": "...",
  "assumption_made": "...",
  "plausible_alternative": "...",
  "evidence_from_sql": "..."
}}

---

# TAXONOMY (MANDATORY)

## 1. Linguistic & Semantic Ambiguity (NL Query)

Occurs when the wording or semantic structure of the question allows multiple interpretations.

### Scope
Quantifiers like "each", "every", "all" are unclear.

Example:
"List students who took every math course."
- A: Students who completed all math courses
- B: Students who completed every course they enrolled in

---

### Attachment
Modifiers can attach to different parts of the sentence.

Example:
"Show employees in departments with managers from Berlin."
- A: Departments are located in Berlin
- B: Managers are from Berlin

---

### Intent
Query does not clearly specify operation (filter, sort, group).

Example:
"Show sales by region."
- A: Total sales per region
- B: Average sales per store in region
- C: Regions ordered by sales

"Show the highest salaries."
- A: Top salary per department
- B: Highest N salaries overall
- C: Salaries above threshold

---

#### Temporal
Time reference is unclear.

Example:
"Show the newest products."
- A: Most recent release date overall
- B: Products from last X years
- C: Recently inserted records

---

## 2. Schema Ambiguity (DB Schema)

Occurs when multiple schema structures can satisfy the query.

---

### Column
Multiple columns match meaning.

Employees(first_name, last_name)

"List names of all personnel."
- A: SELECT first_name
- B: SELECT last_name

---

### Table
Multiple tables match meaning.

Employees(name)
Staff(name)

"List names of all personnel."
- A: Employees
- B: Staff

---

### Join
Multiple relational paths exist.

Employees(id, first_name, last_name)
Profiles(employee_id, full_name)

"List full names of all employees."
- A: Use Employees table only
- B: Join Profiles table

---

### Aggregate
Precomputed vs raw aggregation conflict.

Employees(department_name, salary)
Departments(name, average_salary)

"Show average salary for IT department."
- A: AVG(salary) from Employees
- B: Use Departments.average_salary

---

## 3. Data Ambiguity (DB Values)

Occurs when values in schema are inconsistent or underspecified.

---

### Value

Departments(location)

"List all departments in NYC."
- A: location = 'NYC'
- B: location = 'New York City'

---

# STRICT RULES

- Only use taxonomy above
- If no ambiguity type fits, return empty array
- Always select the BEST matching type
- Do NOT create new ambiguity categories
- Always ground evidence_from_sql in actual SQL output
- Always include at least one ambiguity if SQL makes assumptions
- Return JSON only (no markdown, no explanation)
"""