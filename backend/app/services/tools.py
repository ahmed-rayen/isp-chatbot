
import json
import os

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")

# backend/app/services/tools.py

def search_knowledge_base(query: str) -> str:
    """Searches the knowledge base for information matching the query."""
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
        
        # Split the query into individual words (e.g., "configure dns" -> ["configure", "dns"])
        query_words = query.lower().split()
        results = []
        
        for item in knowledge:
            # Combine topic, tags, and content into one big lowercase string to search
            searchable_text = (item["topic"] + " " + " ".join(item["tags"]) + " " + item["content"]).lower()
            
            # If ANY word from the query is in the text, we consider it a match!
            if any(word in searchable_text for word in query_words):
                results.append(item["content"])
        
        if results:
            # Join all matching results
            return "\n\n".join(results)
        else:
            return "No information found in the knowledge base for this query."
            
    except Exception as e:
        return f"Error reading knowledge base: {str(e)}"

#Update the Tool Definitions
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the ISP knowledge base for technical guides, router setup, DNS configuration, and billing plans. Use this whenever a user asks a 'how-to' question or about prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term, e.g., 'dns', 'router reset', 'fiber plans'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

#Update the router
def execute_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "check_outage":
        return check_outage(**arguments)
    elif tool_name == "create_ticket":
        return create_ticket(**arguments)
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(**arguments)
    else:
        return "Tool not found."