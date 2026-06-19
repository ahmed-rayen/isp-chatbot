# backend/app/services/nvidia_client.py
from openai import OpenAI
from app.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT
from fastapi.responses import StreamingResponse

client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

def get_ai_response(chat_history: list) -> str:
    # (Keep the old non-streaming function as a fallback)
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history
    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.3,
            max_tokens=512,
            top_p=0.9
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Error connecting to AI."

# backend/app/services/nvidia_client.py
def stream_ai_response(chat_history: list):
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history
    
    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.3,
            max_tokens=512,
            top_p=0.9,
            stream=True
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        # Print the real error to your terminal, but DON'T send it to the chat UI!
        print(f"STREAMING ENDED OR ERROR: {e}")git branch -M main