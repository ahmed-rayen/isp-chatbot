# backend/evaluations/eval_tool_routing.py
import json
from app.config import settings
from app.services.tools import TOOL_DEFINITIONS
from openai import OpenAI

# Initialize client directly for testing
client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

# Our system prompt for the test
SYSTEM_PROMPT = """
CRITICAL INSTRUCTION: YOU MUST REPLY IN THE EXACT SAME LANGUAGE AS THE USER'S MESSAGE.
You are OassisBot, an expert Technical Support AI for an Internet Service Provider. 
If a user asks a 'how-to' question OR asks about prices/plans, you MUST use the 'search_knowledge_base' tool.
If a user asks about an outage, use 'check_outage'.
If a user explicitly asks to escalate or create a ticket, use 'create_ticket'.
"""

# The Test Cases
TEST_CASES = [
    {
        "message": "My wifi keeps cutting out when I go to the kitchen.",
        "expected_tool": "search_knowledge_base",
        "expected_args_contains": {"query": "wifi"}, # We just check if the query contains 'wifi'
        "description": "Semantic match for Wi-Fi optimization (no exact keyword match)"
    },
    {
        "message": "Is there a problem in Sfax right now?",
        "expected_tool": "check_outage",
        "expected_args_contains": {"city": "sfax"},
        "description": "Outage check with specific city extraction"
    },
    {
        "message": "I want a human to call me, please open a ticket. My number is 5551234.",
        "expected_tool": "create_ticket",
        "expected_args_contains": {"issue_summary": "call"},
        "description": "Explicit ticket escalation request"
    },
    {
        "message": "What are the prices for your 1 gigabit fiber plans?",
        "expected_tool": "search_knowledge_base",
        "expected_args_contains": {"query": "plan"},
        "description": "Billing question routed to KB instead of hallucinating prices"
    },
    {
        "message": "The red LOS light is flashing on my modem.",
        "expected_tool": "search_knowledge_base",
        "expected_args_contains": {"query": "los"}, # or "light" or "router"
        "description": "Technical diagnosis routed to KB for router lights guide"
    }
]

def run_evaluation():
    print("--- 🧪 STARTING AI TOOL ROUTING EVALUATION ---\n")
    passed = 0
    
    for i, test in enumerate(TEST_CASES):
        print(f"Test {i+1}: {test['description']}")
        print(f"User Input: '{test['message']}'")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": test["message"]}
        ]
        
        try:
            # 1. Call the API
            response = client.chat.completions.create(
                model=settings.nvidia_model,
                messages=messages,
                temperature=0.0, # 0 temperature for deterministic testing
                tools=TOOL_DEFINITIONS
            )
            
            message = response.choices[0].message
            
            # 2. Check if a tool was called
            if not message.tool_calls:
                print(f"❌ FAIL: AI did not call a tool. It replied with: '{message.content[:50]}...'\n")
                continue
                
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # 3. Validate the Tool Name
            if tool_name != test["expected_tool"]:
                print(f"❌ FAIL: Called '{tool_name}', but expected '{test['expected_tool']}'\n")
                continue
                
            # 4. Validate the Arguments
            args_match = True
            for key, expected_val in test["expected_args_contains"].items():
                actual_val = tool_args.get(key, "").lower()
                if expected_val not in actual_val:
                    args_match = False
                    break
                    
            if not args_match:
                print(f"❌ FAIL: Called correct tool, but args were wrong. Got: {tool_args}\n")
                continue
                
            print(f"✅ PASS: Called '{tool_name}' with args {tool_args}\n")
            passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: API Error - {e}\n")
            
    print("--- 🧪 EVALUATION COMPLETE ---")
    print(f"Score: {passed}/{len(TEST_CASES)} Passed\n")

if __name__ == "__main__":
    # Allows us to run: python -m evaluations.eval_tool_routing
    run_evaluation()