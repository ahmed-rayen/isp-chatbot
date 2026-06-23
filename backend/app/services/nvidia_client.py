# backend/app/services/nvidia_client.py
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.tools import TOOL_DEFINITIONS, execute_tool
from app.models.db_models import SessionSummary 
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError
import asyncio
client = AsyncOpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

async def get_ai_response_with_tools(db: Session, session_id: str, chat_history: list, transcript_str: str, user_id: str):
    recent_history = chat_history[-6:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_history

    # Fetch past summaries
    past_summaries = db.query(SessionSummary).filter(SessionSummary.user_id == user_id).order_by(SessionSummary.created_at.desc()).limit(3).all()
    if past_summaries:
        memory_text = "Previous recent interactions with this user:\n"
        for s in reversed(past_summaries):
            memory_text += f"- {s.summary}\n"
        messages.insert(1, {"role": "system", "content": memory_text})

    if transcript_str:
        messages.append({"role": "system", "content": f"If you decide to use the create_ticket tool, use the following text as the 'transcript' argument:\n{transcript_str}"})

    max_retries = 2
    for attempt in range(max_retries):
        try:
            # AWAIT the initial API call
            response = await client.chat.completions.create(
                model=settings.nvidia_model,
                messages=messages,
                temperature=0.3,
                max_tokens=512,
                tools=TOOL_DEFINITIONS
            )

            message = response.choices[0].message

            if message.tool_calls:
                messages.append(message.model_dump())
                guardrail_triggered = False  # Track if any tool call fails validation
                
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # --- GUARDRAIL FOR SCHEDULING ---
                    if tool_name == "schedule_technician_visit":
                        if not tool_args.get("preferred_date") or not tool_args.get("time_slot"):
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": "Error: Missing preferred_date or time_slot. You MUST ask the user for their preferred date and time slot (morning, afternoon, or evening) before calling this tool. Do not apologize, just ask for the date and time."
                            })
                            guardrail_triggered = True
                            continue  # Skip execution of this specific invalid tool call

                    # Run standard execution if guardrail didn't catch it
                    print(f"AI is calling tool: {tool_name} with args {tool_args}")
                    tool_result = execute_tool(db, session_id, user_id, tool_name, tool_args, transcript_str)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result
                    })
                
                # AWAIT the final API call to respond back to the user with the tool outcomes/errors
                final_response = await client.chat.completions.create(
                    model=settings.nvidia_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=512
                )
                return final_response.choices[0].message.content

            return message.content

        except (APIConnectionError, RateLimitError, APIError) as e:
            print(f"⚠️ NVIDIA API Error (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # Secure async delay
            else:
                return "I'm sorry, our systems are currently experiencing high traffic. Please try again in a moment."
            
async def generate_session_summary(chat_history: list):
    messages = [
        {"role": "system", "content": "You are a summarization AI. Read the conversation and output a 2-3 sentence summary. Format it EXACTLY as: 'Issue: [description]. Resolution: [description]. Status: [resolved/unresolved]. Ticket ID: [TKT-XXXXX or None]'."},
        {"role": "user", "content": str(chat_history)}
    ]
    try:
        response = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.1,
            max_tokens=150
        )
        text = response.choices[0].message.content
        status = "unresolved"
        if "status: resolved" in text.lower():
            status = "resolved"
        return text, status
    except Exception as e:
        return "Failed to summarize.", "unresolved"

def generate_session_summary(chat_history: list):
    """Asks the AI to summarize the conversation for future context."""
    messages = [
        {"role": "system", "content": "You are a summarization AI. Read the conversation and output a 2-3 sentence summary. Format it EXACTLY as: 'Issue: [description]. Resolution: [description]. Status: [resolved/unresolved]. Ticket ID: [TKT-XXXXX or None]'."},
        {"role": "user", "content": str(chat_history)}
    ]
    
    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=messages,
            temperature=0.1,
            max_tokens=150
        )
        text = response.choices[0].message.content
        
        status = "unresolved"
        if "status: resolved" in text.lower():
            status = "resolved"
            
        return text, status
    except Exception as e:
        return "Failed to summarize.", "unresolved"