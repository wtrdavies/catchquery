"""
MMO Fish Landings Query Engine

Takes natural language questions and converts them to SQL queries
against the MMO landings database.
"""

import sqlite3
import json
from anthropic import Anthropic

# Database schema description for the LLM
SCHEMA_DESCRIPTION = """
You have access to a SQLite database with UK fish landing statistics.

TABLE: landings
- year (INTEGER): Year of landing (e.g., 2024)
- month (INTEGER): Month of landing (1-12)
- port (TEXT): Name of port where fish was landed (e.g., 'Peterhead', 'Plymouth', 'Newlyn')
- port_nationality (TEXT): Which region/country the port is in. Values include:
  'UK - Scotland', 'UK - England', 'UK - Wales', 'UK - Northern Ireland', 
  'UK - Isle of Man', 'UK - Channel Islands', 'Norway', 'Denmark', 'Netherlands', 
  'Ireland', 'France', 'Spain', 'Belgium', 'Iceland', 'Faeroe Islands', 'Canada'
- vessel_nationality (TEXT): Nationality of the fishing vessel (same values as port_nationality)
- length_group (TEXT): Vessel size - either '10m&Under' or 'Over10m'
- gear_category (TEXT): Fishing method - e.g., 'Trawl', 'Dredges', 'Traps', 'Nets', 'Lines', 'Seines'
- species_code (TEXT): Short code for species (e.g., 'MAC' for Mackerel)
- species_name (TEXT): Full species name (e.g., 'Mackerel', 'Cod', 'Lobsters', 'Scallops')
- species_group (TEXT): Category - 'Pelagic', 'Demersal', 'Shellfish'
- live_weight_tonnes (REAL): Weight of catch in tonnes (live weight)
- landed_weight_tonnes (REAL): Weight actually landed in tonnes
- value_thousands (REAL): Value in thousands of pounds (£)

IMPORTANT NOTES:
- When users say "Scotland" they likely mean port_nationality = 'UK - Scotland'
- Value is in THOUSANDS of pounds, so multiply by 1000 or note this in your response
- For "average price per tonne", calculate SUM(value_thousands) / SUM(live_weight_tonnes) * 1000
- Use LIKE with wildcards for partial species matches (e.g., WHERE species_name LIKE '%Crab%')
- Always use ROUND() for numerical outputs
- The data currently only contains 2024 data
"""

SYSTEM_PROMPT = f"""You are a helpful assistant that converts natural language questions about UK fish landings into SQL queries.

{SCHEMA_DESCRIPTION}

When given a question:
1. First, write a brief explanation of what you understand the user is asking
2. Then provide the SQL query inside <sql></sql> tags
3. The SQL must be valid SQLite syntax

If the question cannot be answered with the available data, explain why.

Examples:

User: How much mackerel was landed in Scotland in 2024?
Assistant: You want to know the total mackerel landings (by weight and value) at Scottish ports in 2024.

<sql>
SELECT 
    ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
    ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings 
WHERE species_name = 'Mackerel' 
  AND port_nationality = 'UK - Scotland'
  AND year = 2024
</sql>

User: What are the top 5 ports for lobster?
Assistant: You want to find which ports land the most lobsters by value.

<sql>
SELECT 
    port,
    port_nationality,
    ROUND(SUM(live_weight_tonnes), 2) as total_tonnes,
    ROUND(SUM(value_thousands) * 1000, 2) as total_value_pounds
FROM landings 
WHERE species_name = 'Lobsters'
GROUP BY port, port_nationality
ORDER BY total_value_pounds DESC
LIMIT 5
</sql>

User: What's the average price per tonne of cod?
Assistant: You want to calculate the average price per tonne for cod across all landings.

<sql>
SELECT 
    ROUND(SUM(value_thousands) * 1000 / SUM(live_weight_tonnes), 2) as avg_price_per_tonne_pounds
FROM landings 
WHERE species_name = 'Cod'
  AND live_weight_tonnes > 0
</sql>
"""


class MMOQueryEngine:
    def __init__(self, db_path: str, api_key: str = None):
        self.db_path = db_path
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
    
    def _get_sql_from_response(self, response_text: str) -> str | None:
        """Extract SQL from between <sql> tags"""
        if '<sql>' not in response_text or '</sql>' not in response_text:
            return None
        start = response_text.index('<sql>') + 5
        end = response_text.index('</sql>')
        return response_text[start:end].strip()
    
    def _run_query(self, sql: str) -> tuple[list[dict], str | None]:
        """Execute SQL and return results as list of dicts"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows, None
        except Exception as e:
            return [], str(e)
    
    def ask(self, question: str) -> dict:
        """
        Main method: takes a natural language question, returns answer.
        
        Returns dict with:
        - question: the original question
        - explanation: what the LLM understood
        - sql: the generated SQL
        - results: query results (list of dicts)
        - error: any error message
        - summary: natural language summary of results
        """
        # Step 1: Get SQL from LLM
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}]
        )
        
        llm_response = response.content[0].text
        sql = self._get_sql_from_response(llm_response)
        
        # Extract explanation (everything before the SQL tags)
        explanation = llm_response.split('<sql>')[0].strip() if sql else llm_response
        
        if not sql:
            return {
                "question": question,
                "explanation": explanation,
                "sql": None,
                "results": [],
                "error": "Could not generate SQL query",
                "summary": explanation
            }
        
        # Step 2: Run the query
        results, error = self._run_query(sql)
        
        if error:
            return {
                "question": question,
                "explanation": explanation,
                "sql": sql,
                "results": [],
                "error": f"SQL error: {error}",
                "summary": f"Query failed: {error}"
            }
        
        # Step 3: Generate a natural language summary of results
        summary = self._summarise_results(question, results)
        
        return {
            "question": question,
            "explanation": explanation,
            "sql": sql,
            "results": results,
            "error": None,
            "summary": summary
        }
    
    def _summarise_results(self, question: str, results: list[dict]) -> str:
        """Generate a natural language summary of the query results"""
        if not results:
            return "No results found."
        
        if len(results) == 1 and len(results[0]) <= 3:
            # Simple single-row result - just format it nicely
            parts = []
            for key, value in results[0].items():
                if isinstance(value, float):
                    if 'pound' in key.lower() or 'value' in key.lower():
                        parts.append(f"{key.replace('_', ' ')}: £{value:,.2f}")
                    else:
                        parts.append(f"{key.replace('_', ' ')}: {value:,.2f}")
                else:
                    parts.append(f"{key.replace('_', ' ')}: {value}")
            return ", ".join(parts)
        
        # For more complex results, let the LLM summarise
        summary_prompt = f"""Given this question: "{question}"

And these query results (as JSON):
{json.dumps(results[:20], indent=2)}

Provide a brief, natural language summary of the findings. Be concise - 2-3 sentences max.
If there are monetary values, format them with £ signs and commas."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": summary_prompt}]
        )
        
        return response.content[0].text


def main():
    """Interactive command-line interface"""
    import os
    
    db_path = "/home/claude/mmo_landings.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    engine = MMOQueryEngine(db_path)
    
    print("=" * 60)
    print("MMO Fish Landings Query Engine")
    print("Ask questions about UK fish landings in natural language.")
    print("Type 'quit' to exit.")
    print("=" * 60)
    print()
    
    while True:
        question = input("Your question: ").strip()
        
        if question.lower() in ('quit', 'exit', 'q'):
            break
        
        if not question:
            continue
        
        print("\nProcessing...")
        result = engine.ask(question)
        
        print(f"\n📊 {result['summary']}")
        
        if result['sql']:
            print(f"\n🔍 SQL used:\n{result['sql']}")
        
        if result['error']:
            print(f"\n❌ Error: {result['error']}")
        
        print("\n" + "-" * 40 + "\n")


if __name__ == "__main__":
    main()
