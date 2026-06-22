# backend/app/services/nvidia_client.py
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.tools import TOOL_DEFINITIONS, execute_tool

client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

def get_ai_response_with_tools(db: Session, session_id: str, chat_history: list, transcript_str: str = "", user_id: str = ""):
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history

    if transcript_str:
        messages.append({"role": "system", "content": f"If you decide to use the create_ticket tool, use the following text as the 'transcript' argument:\n{transcript_str}"})

    # Inject authenticated user_id so tools never receive "guest"
    if user_id:
        messages.append({"role": "system", "content": f"The authenticated user's ID is: {user_id}. Use this value when calling get_account_status or create_ticket."})

    response = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=messages,
        temperature=0.3,
        max_tokens=512,
        tools=TOOL_DEFINITIONS
    )
    message = response.choices[0].message

    # 2. Check if AI wants to call a tool
    if message.tool_calls:
        messages.append(message.model_dump())
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            print(f"AI is calling tool: {tool_name} with args {tool_args}")
            tool_result = execute_tool(db, session_id, user_id, tool_name, tool_args)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": tool_result
            })
        
        # 3. Second call to AI to format the result
        final_response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.3,
            max_tokens=512
        )
        return final_response.choices[0].message.content

    # 4. If no tool called, return normal text
    return message.content