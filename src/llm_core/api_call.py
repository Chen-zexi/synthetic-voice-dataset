from typing import Any, Dict, Optional, Type, Union, Tuple
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


def extract_token_usage(response: Any) -> Dict[str, Any]:
    """Extract token usage information from a response object.
    
    Args:
        response: Response object from LangChain
        
    Returns:
        Dictionary containing comprehensive token usage information
    """
    token_info = {}
    
    # Try to get usage_metadata (primary source for Response API)
    if hasattr(response, 'usage_metadata'):
        usage = response.usage_metadata
        if isinstance(usage, dict):
            token_info['input_tokens'] = usage.get('input_tokens', 0)
            token_info['output_tokens'] = usage.get('output_tokens', 0)
            token_info['total_tokens'] = usage.get('total_tokens', 0)
            
            # Extract cached tokens from input_token_details (Response API format)
            if 'input_token_details' in usage:
                details = usage['input_token_details']
                if 'cache_read' in details:
                    token_info['cached_tokens'] = details.get('cache_read', 0)
                if 'audio' in details:
                    token_info['audio_input_tokens'] = details.get('audio', 0)
            
            # Extract output token details
            if 'output_token_details' in usage:
                details = usage['output_token_details']
                if 'reasoning' in details:
                    token_info['reasoning_tokens'] = details.get('reasoning', 0)
                if 'audio' in details:
                    token_info['audio_output_tokens'] = details.get('audio', 0)
    
    # Also check response_metadata for additional details (Standard API)
    if hasattr(response, 'response_metadata'):
        metadata = response.response_metadata
        if isinstance(metadata, dict) and 'token_usage' in metadata:
            token_usage = metadata['token_usage']
            
            # Fallback if usage_metadata was not available
            if 'input_tokens' not in token_info:
                token_info['input_tokens'] = token_usage.get('prompt_tokens', 0)
                token_info['output_tokens'] = token_usage.get('completion_tokens', 0)
                token_info['total_tokens'] = token_usage.get('total_tokens', 0)
            
            # Extract prompt token details (Standard API format)
            if 'prompt_tokens_details' in token_usage:
                details = token_usage['prompt_tokens_details']
                if 'cached_tokens' in details:
                    # Prefer this over cache_read if both exist
                    token_info['cached_tokens'] = details.get('cached_tokens', 0)
                if 'audio_tokens' in details:
                    token_info['audio_input_tokens'] = details.get('audio_tokens', 0)
            
            # Extract completion token details (Standard API format)
            if 'completion_tokens_details' in token_usage:
                details = token_usage['completion_tokens_details']
                if 'reasoning_tokens' in details:
                    token_info['reasoning_tokens'] = details.get('reasoning_tokens', 0)
                if 'accepted_prediction_tokens' in details:
                    token_info['accepted_prediction_tokens'] = details.get('accepted_prediction_tokens', 0)
                if 'rejected_prediction_tokens' in details:
                    token_info['rejected_prediction_tokens'] = details.get('rejected_prediction_tokens', 0)
                if 'audio_tokens' in details:
                    token_info['audio_output_tokens'] = details.get('audio_tokens', 0)
    
    return token_info


async def make_api_call(
    llm: object,
    system_prompt: str,
    user_prompt: str,
    response_schema: Optional[Type[BaseModel]] = None,
    return_token_usage: bool = False,
) -> Union[BaseModel, str, Tuple[Any, Dict[str, Any]]]:
    """
    Make an async API call to an LLM with structured output support.
    
    Args:
        llm: The LLM instance
        system_prompt: System prompt
        user_prompt: User prompt
        response_schema: Optional Pydantic schema for structured output
        return_token_usage: If True, returns tuple of (response, token_usage)
        
    Returns:
        Structured response as Pydantic model or raw string
        If return_token_usage=True, returns tuple of (response, token_usage)
    """
    messages = create_prompt_template(system_prompt, user_prompt)
    
    # Case 1: No schema requested, return raw content
    if response_schema is None:
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        if return_token_usage:
            token_info = extract_token_usage(response)
            return content, token_info
        return content
    
    # Case 2: Try native structured output first
    try:
        # Try with include_raw=True to get token usage
        try:
            client = llm.with_structured_output(response_schema, include_raw=True)
            response_with_raw = await client.ainvoke(messages)
            
            # Extract the parsed response and raw response
            if isinstance(response_with_raw, dict) and 'raw' in response_with_raw:
                response = response_with_raw.get('parsed', response_with_raw)
                raw_response = response_with_raw['raw']
                token_info = extract_token_usage(raw_response)
            else:
                # Fallback if include_raw didn't work
                response = response_with_raw
                token_info = {}
        except:
            # Fallback to regular structured output
            client = llm.with_structured_output(response_schema)
            response = await client.ainvoke(messages)
            token_info = {}
        
        if return_token_usage:
            return response, token_info
        return response
    except Exception as e:
        # Case 3: Fallback to JSON parsing
        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract token usage
            token_info = extract_token_usage(response)
            
            # Try to extract JSON from the response
            data = extract_json(content)
            parsed = response_schema(**data)
            
            if return_token_usage:
                return parsed, token_info
            return parsed
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
    
