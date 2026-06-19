# backend/app/services/nvidia_client.py
import json
from openai import OpenAI
from app.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.tools import TOOL_DEFINITIONS, execute_tool

client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

def get_ai_response_with_tools(chat_history: list):
    """
    Checks if the AI wants to use a tool. 
    If yes, runs the tool and returns the final text.
    If no, returns the normal text response.
    """
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history

    # 1. First call to the AI WITH tools attached
    response = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=messages,
        temperature=0.3,
        max_tokens=512,
        tools=TOOL_DEFINITIONS
    )

    message = response.choices[0].message

    # 2. Check if the AI decided to call a tool
    if message.tool_calls:
        # We need to execute the tool and send the result back to the AI
        
        # Append the AI's request to call the tool to our messages
        messages.append(message.model_dump())
        
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # Run the actual Python function!
            print(f"AI is calling tool: {tool_name} with args {tool_args}")
            tool_result = execute_tool(tool_name, tool_args)
            
            # Send the tool result back to the AI
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": tool_result
            })
        
        # 3. Second call to the AI so it can format the tool result into a nice message
        final_response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.3,
            max_tokens=512
        )
        return final_response.choices[0].message.content

    # 4. If no tool was called, just return the text
    return message.content

# Keep the old streaming function for later, but we'll use the one above for now
def stream_ai_response(chat_history: list):
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history
    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.3,
            max_tokens=512,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"STREAMING ERROR: {e}")