import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import httpx
# from ..exceptions import MissingAPIKeyError, InvalidProviderError

load_dotenv()


class LLM:
    """A factory class for creating LangChain LLM clients for various providers."""
    def __init__(self, provider: str, model: str, temperature: float = 1.0, 
                 max_tokens: int = None, top_p: float = 0.95, n: int = 1):
        """
        Initializes the LLM factory.

        Args:
            provider: The name of the LLM provider (e.g., 'openai', 'lm-studio').
            model: The specific model name to use.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum number of tokens to generate.
            top_p: Nucleus sampling probability.
            n: Number of completions to generate.
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.n = n

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
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            
            # Create custom httpx clients to fix async cleanup issues
            # These clients will properly close connections
            http_client = httpx.Client(
                headers={"Connection": "close"},
                timeout=30.0
            )
            http_async_client = httpx.AsyncClient(
                headers={"Connection": "close"},
                timeout=30.0
            )
            
            return ChatOpenAI(
                api_key=api_key, 
                model=self.model, 
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                n=self.n,
                # Custom clients with proper connection handling
                http_client=http_client,
                http_async_client=http_async_client,
                # Also set default headers as backup
                default_headers={"Connection": "close"}
            )
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
            if self.model.startswith("gemini-2.5-flash"):
                return ChatGoogleGenerativeAI(
                    api_key=api_key, 
                    model=self.model, 
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    n=self.n
                )
            else:
                return ChatGoogleGenerativeAI(
                    api_key=api_key, 
                    model=self.model, 
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
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
        
    def get_structure_model(self, provider: str = None):
        """Get a model for structure parsing. Defaults to OpenAI gpt-4.1-nano."""
        # Always use OpenAI gpt-4.1-nano for structure parsing by default
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set (required for structure model parsing)")
        return ChatOpenAI(api_key=api_key, model="gpt-4.1-nano", temperature=0)
        
    def get_structure_model_legacy(self, provider: str):
        """Legacy method for getting provider-specific structure models."""
        if provider == "lm-studio":
            host_ip = os.getenv("HOST_IP")
            if not host_ip:
                raise ValueError("HOST_IP is not set for legacy LM-Studio structure model")
            return ChatOpenAI(base_url=f"http://{host_ip}:1234/v1", api_key='lm-studio', model='osmosis-structure-0.6b@f16', temperature=0)
        elif provider == "vllm":
            # Assume using lm-studio
            host_ip = os.getenv("HOST_IP")
            if not host_ip:
                raise ValueError("HOST_IP is not set for legacy vLLM structure model")
            print(f"http://{host_ip}:8000/v1")
            return ChatOpenAI(base_url=f"http://{host_ip}:8000/v1", api_key='EMPTY', model='osmosis-structure-0.6b@f16', temperature=0)
        else:
            raise ValueError(f"Unsupported provider for structure model: {provider}")