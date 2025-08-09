import os
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import httpx

load_dotenv()


class ModelConfig:
    """Manages model configuration from JSON file."""
    
    def __init__(self):
        config_path = Path(__file__).parent / "model_config.json"
        with open(config_path, 'r') as f:
            self.config = json.load(f)
    
    def get_models(self, provider: str) -> List[Dict]:
        """Get list of models for a provider."""
        return self.config["models"].get(provider, [])
    
    def get_model_info(self, provider: str, model_id: str) -> Optional[Dict]:
        """Get information about a specific model."""
        models = self.get_models(provider)
        for model in models:
            if model["id"] == model_id:
                return model
        return None
    
    def get_model_parameters(self, provider: str, model_id: str) -> Dict[str, Any]:
        """Get default parameters for a specific model."""
        model_info = self.get_model_info(provider, model_id)
        if model_info:
            # Extract defaults from parameter definitions
            defaults = {}
            parameters = model_info.get("parameters", {})
            for param_name, param_def in parameters.items():
                if "default" in param_def:
                    defaults[param_name] = param_def["default"]
            return defaults
        
        # For dynamic models (lm-studio, vllm), use provider defaults
        provider_config = self.get_provider_config(provider)
        return provider_config.get("default_parameters", {"temperature": 0})
    
    def get_supported_parameters(self, provider: str, model_id: str) -> List[str]:
        """Get list of supported parameters for a model."""
        model_info = self.get_model_info(provider, model_id)
        if model_info and "parameters" in model_info:
            return list(model_info["parameters"].keys())
        return []
    
    def get_unsupported_parameters(self, provider: str, model_id: str) -> List[str]:
        """Get list of unsupported parameters for a model."""
        model_info = self.get_model_info(provider, model_id)
        if model_info:
            return model_info.get("unsupported_parameters", [])
        return []
    
    def is_reasoning_model(self, provider: str, model_id: str) -> bool:
        """Check if a model is a reasoning model."""
        model_info = self.get_model_info(provider, model_id)
        return model_info.get("is_reasoning", False) if model_info else False
    
    def get_provider_config(self, provider: str) -> Dict:
        """Get provider configuration."""
        return self.config["provider_config"].get(provider, {})
    
    def get_model_pricing(self, provider: str, model_id: str) -> Optional[Dict[str, Any]]:
        """Get pricing information for a specific model.
        
        Returns:
            Dictionary with pricing info or None if not available
        """
        model_info = self.get_model_info(provider, model_id)
        if model_info and 'pricing' in model_info:
            return model_info['pricing']
        return None


class LLM:
    """A factory class for creating LangChain LLM clients for various providers."""
    
    # Class-level model config instance
    _model_config = None
    
    @classmethod
    def get_model_config(cls) -> ModelConfig:
        """Get or create the model configuration singleton."""
        if cls._model_config is None:
            cls._model_config = ModelConfig()
        return cls._model_config
    
    def __init__(self, provider: str, model: str, use_response_api: Optional[bool] = None, **kwargs):
        """
        Initializes the LLM factory with intelligent parameter filtering.

        Args:
            provider: The name of the LLM provider (e.g., 'openai', 'lm-studio').
            model: The specific model name to use.
            use_response_api: Whether to use OpenAI's Response API (default True for OpenAI).
            **kwargs: Additional parameters (will be filtered based on model support).
        """
        self.provider = provider
        self.model = model
        # Default to True for OpenAI provider if not specified
        if use_response_api is None:
            self.use_response_api = (provider == "openai")
        else:
            self.use_response_api = use_response_api
        
        # Load model configuration
        try:
            self.model_config = self.get_model_config()
            model_info = self.model_config.get_model_info(provider, model)
            
            # Get supported and unsupported parameters for this model
            supported_params = self.model_config.get_supported_parameters(provider, model)
            unsupported_params = self.model_config.get_unsupported_parameters(provider, model)
            model_defaults = self.model_config.get_model_parameters(provider, model)
            
            # Initialize parameter storage
            self.model_parameters = {}
            
            # First, apply model-specific defaults
            for param_name, default_value in model_defaults.items():
                self.model_parameters[param_name] = default_value
            
            # Then, override with provided parameters (if supported)
            for param_name, param_value in kwargs.items():
                # Skip LLM-specific prefixes if present
                clean_param = param_name.replace('llm_', '') if param_name.startswith('llm_') else param_name
                
                # Check if parameter is supported
                if model_info:
                    if clean_param in unsupported_params:
                        # Silently skip unsupported parameters
                        continue
                    elif supported_params and clean_param not in supported_params:
                        # If we have a supported list and param isn't in it, skip
                        continue
                
                # Apply the parameter
                self.model_parameters[clean_param] = param_value
            
            # Set commonly used attributes for backward compatibility
            self.temperature = self.model_parameters.get('temperature', 1.0)
            self.max_tokens = self.model_parameters.get('max_tokens') or self.model_parameters.get('max_completion_tokens')
            self.top_p = self.model_parameters.get('top_p', 0.95)
            self.n = self.model_parameters.get('n', 1)
            
        except Exception as e:
            # Fallback to basic parameters if config loading fails
            self.model_parameters = {
                'temperature': kwargs.get('temperature', kwargs.get('llm_temperature', 1.0)),
                'max_tokens': kwargs.get('max_tokens', kwargs.get('llm_max_tokens')),
                'top_p': kwargs.get('top_p', kwargs.get('llm_top_p', 0.95)),
                'n': kwargs.get('n', kwargs.get('llm_n', 1))
            }
            self.temperature = self.model_parameters['temperature']
            self.max_tokens = self.model_parameters['max_tokens']
            self.top_p = self.model_parameters['top_p']
            self.n = self.model_parameters['n']

    def get_llm(self):
        """
        Initializes and returns a LangChain LLM client for the configured provider.

        Returns:
            A LangChain chat model instance.

        Raises:
            MissingAPIKeyError: If required API keys are not set.
            InvalidProviderError: If the provider is unsupported.
        """
        if self.provider == "openai":
            params = self._prepare_openai_params()
            
            # Extract special parameters that need to go in model_kwargs
            reasoning_param = params.pop("reasoning", None)
            existing_model_kwargs = params.pop("model_kwargs", {})
            
            # Combine model_kwargs if we have reasoning params or Response API
            if reasoning_param or existing_model_kwargs:
                combined_model_kwargs = existing_model_kwargs.copy()
                if reasoning_param:
                    combined_model_kwargs["reasoning"] = reasoning_param
                
                # Use model_kwargs for special parameters
                # Suppress the warning about parameters in model_kwargs
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="Parameters .* should be specified explicitly")
                    llm = ChatOpenAI(**params, model_kwargs=combined_model_kwargs)
            else:
                # Standard case without special parameters
                llm = ChatOpenAI(**params)
            
            return llm
        elif self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            return ChatAnthropic(
                api_key=api_key, 
                model=self.model, 
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                model_kwargs={"top_p": self.top_p}
            )
        elif self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set")
            
            # Gemini uses max_output_tokens instead of max_tokens
            max_output = self.max_tokens or self.model_parameters.get('max_output_tokens')
            
            return ChatGoogleGenerativeAI(
                api_key=api_key, 
                model=self.model, 
                temperature=self.temperature,
                max_output_tokens=max_output,  # Use max_output_tokens for Gemini
                top_p=self.top_p,
                n=self.n
            )
        elif self.provider == "lm-studio":
            host_ip = os.getenv("HOST_IP")
            if not host_ip:
                raise ValueError("HOST_IP environment variable is not set for LM-Studio")
            return ChatOpenAI(
                base_url=f"http://{host_ip}:1234/v1", 
                api_key='lm-studio', 
                model=self.model, 
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                n=self.n
            )
        elif self.provider == "vllm":
            # Assume using lm-studio
            host_ip = os.getenv("HOST_IP")
            if not host_ip:
                raise ValueError("HOST_IP environment variable is not set for vLLM")
            print(f"http://{host_ip}:8000/v1")
            return ChatOpenAI(
                base_url=f"http://{host_ip}:8000/v1", 
                api_key='EMPTY', 
                model=self.model, 
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                n=self.n
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Supported: openai, anthropic, gemini, lm-studio, vllm")
    
    def _create_http_clients(self) -> tuple:
        """Create HTTP clients with proper connection handling."""
        http_client = httpx.Client(
            headers={"Connection": "close"},
            timeout=30.0
        )
        http_async_client = httpx.AsyncClient(
            headers={"Connection": "close"},
            timeout=30.0
        )
        return http_client, http_async_client
    
    def _prepare_openai_params(self) -> Dict[str, Any]:
        """Prepare parameters for OpenAI models."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Create custom httpx clients to fix async cleanup issues
        http_client, http_async_client = self._create_http_clients()
        
        params = {
            "api_key": api_key,
            "model": self.model,
            "stream_usage": True,  # Enable token usage tracking by default
            # Custom clients with proper connection handling
            "http_client": http_client,
            "http_async_client": http_async_client,
            # Also set default headers as backup
            "default_headers": {"Connection": "close"}
        }
        
        # Handle Response API if requested (default True for OpenAI)
        if self.use_response_api:
            # Add output_version parameter for Response API
            params["model_kwargs"] = {
                "output_version": "responses/v1"
            }
        
        # Handle model-specific parameters
        try:
            model_info = self.model_config.get_model_info(self.provider, self.model)
        except:
            model_info = None
        
        if model_info and model_info.get("is_reasoning"):
            # For reasoning models (GPT-5, O3, O4-mini, etc.)
            
            # Build the reasoning parameter structure
            if "reasoning_effort" in self.model_parameters:
                # Pass reasoning as a direct parameter with nested structure
                params["reasoning"] = {
                    "effort": self.model_parameters["reasoning_effort"]
                }
            
            # Handle max_completion_tokens for O-series models
            if "max_completion_tokens" in self.model_parameters:
                params["max_tokens"] = self.model_parameters["max_completion_tokens"]
            elif "max_tokens" in self.model_parameters:
                params["max_tokens"] = self.model_parameters["max_tokens"]
                
        else:
            # For standard models, apply normal parameters
            if "temperature" in self.model_parameters:
                params["temperature"] = self.model_parameters["temperature"]
            if "top_p" in self.model_parameters:
                params["top_p"] = self.model_parameters["top_p"]
            if "presence_penalty" in self.model_parameters:
                params["presence_penalty"] = self.model_parameters["presence_penalty"]
            if "frequency_penalty" in self.model_parameters:
                params["frequency_penalty"] = self.model_parameters["frequency_penalty"]
            if "max_tokens" in self.model_parameters:
                params["max_tokens"] = self.model_parameters["max_tokens"]
            if "n" in self.model_parameters:
                params["n"] = self.model_parameters["n"]
        
        return params