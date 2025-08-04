from typing import Any, Dict, Optional, Type, Union
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
import json


def create_prompt_template(system_prompt: str, user_prompt: str) -> ChatPromptTemplate:
    """Create a standardized prompt template."""
    template = ChatPromptTemplate([
        ("system", "{system_prompt}"),
        ("user", "{user_prompt}")
    ])
    return template.invoke({"system_prompt": system_prompt, "user_prompt": user_prompt})


async def make_api_call(
    llm: object,
    system_prompt: str,
    user_prompt: str,
    response_schema: Optional[Type[BaseModel]] = None,
) -> Union[BaseModel, str]:
    """
    Make an async API call to an LLM with structured output support.
    
    Args:
        llm: The LLM instance
        system_prompt: System prompt
        user_prompt: User prompt
        response_schema: Optional Pydantic schema for structured output
        
    Returns:
        Structured response as Pydantic model or raw string
    """
    messages = create_prompt_template(system_prompt, user_prompt)
    
    # Case 1: No schema requested, return raw content
    if response_schema is None:
        response = await llm.ainvoke(messages)
        return response.content if hasattr(response, 'content') else str(response)
    
    # Case 2: Try native structured output first
    try:
        client = llm.with_structured_output(response_schema)
        response = await client.ainvoke(messages)
        return response
    except Exception as e:
        # Case 3: Fallback to JSON parsing
        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from the response
            data = extract_json(content)
            return response_schema(**data)
        except Exception as parse_error:
            # If all else fails, raise the original error
            raise ValueError(f"Failed to get structured output: {str(e)}. JSON parsing also failed: {str(parse_error)}")


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from text, handling common LLM response patterns.
    
    Args:
        text: Raw text that may contain JSON
        
    Returns:
        Parsed JSON as dictionary
    """
    # Try direct JSON parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON between code blocks
    import re
    json_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON object or array in the text
    # Look for JSON that starts with { and ends with }
    start_idx = text.find('{')
    if start_idx != -1:
        # Try to find matching closing brace
        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(text[start_idx:i+1])
                    except json.JSONDecodeError:
                        break
    
    # If all else fails, raise an error
    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")
    
