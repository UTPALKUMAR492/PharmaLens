"""
PharmaLens LLM Service
======================
Unified interface for LLM calls with retry logic, rate limiting, and error handling.
Supports both OpenAI (cloud) and Llama (local) models.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 60, time_window: int = 60):
        """
        Args:
            max_calls: Maximum number of calls allowed in time_window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Wait if rate limit is exceeded"""
        now = time.time()
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        if len(self.calls) >= self.max_calls:
            # Calculate how long to wait
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call) + 0.1
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            return await self.acquire()
        
        self.calls.append(now)


class LLMService:
    """
    Unified LLM service supporting OpenAI and Llama models.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting to prevent API throttling
    - Error handling and fallback mechanisms
    - Support for both cloud and local models
    """
    
    def __init__(self):
        self.openai_client = None
        self.llama_model = None
        self.rate_limiter = RateLimiter(max_calls=50, time_window=60)
        self._initialized = False
    
    def _init_openai(self, api_key: str):
        """Initialize OpenAI client"""
        if not self.openai_client:
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
    
    def _init_llama(self, model_path: str):
        """Initialize Llama model"""
        if not self.llama_model and model_path:
            try:
                from llama_cpp import Llama
                self.llama_model = Llama(
                    model_path=model_path,
                    n_ctx=8192,  # Context window
                    n_threads=4,  # Number of CPU threads
                    n_gpu_layers=0,  # Use CPU only (set to -1 for GPU)
                )
                logger.info(f"Llama model loaded from {model_path}")
            except ImportError:
                logger.error("llama-cpp-python not installed. Run: pip install llama-cpp-python")
                raise
            except Exception as e:
                logger.error(f"Failed to load Llama model: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_completion(
        self,
        prompt: str,
        llm_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate completion using configured LLM (OpenAI or Llama).
        
        Args:
            prompt: User prompt/query
            llm_config: LLM configuration from PrivacyManager
            system_prompt: Optional system instruction
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Generated text response
        """
        provider = llm_config.get("provider", "openai")
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        try:
            if provider == "openai":
                return await self._generate_openai(
                    prompt=prompt,
                    llm_config=llm_config,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif provider == "local":
                return await self._generate_llama(
                    prompt=prompt,
                    llm_config=llm_config,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", provider=provider)
            raise
    
    async def _generate_openai(
        self,
        prompt: str,
        llm_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate completion using OpenAI API"""
        
        # Initialize OpenAI client if needed
        api_key = llm_config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        self._init_openai(api_key)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Call OpenAI API
        try:
            response = await self.openai_client.chat.completions.create(
                model=llm_config.get("model", "gpt-4"),
                messages=messages,
                temperature=temperature or llm_config.get("temperature", 0.7),
                max_tokens=max_tokens or llm_config.get("max_tokens", 4096),
            )
            
            result = response.choices[0].message.content
            logger.info(
                "OpenAI completion generated",
                model=llm_config.get("model"),
                tokens=response.usage.total_tokens
            )
            return result
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _generate_llama(
        self,
        prompt: str,
        llm_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate completion using local Llama model"""
        
        # Initialize Llama model if needed
        model_path = llm_config.get("model_path")
        if not model_path:
            raise ValueError("Local model path not configured")
        
        self._init_llama(model_path)
        
        # Construct full prompt with system instruction
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = f"User: {prompt}\n\nAssistant:"
        
        # Run inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.llama_model(
                    full_prompt,
                    max_tokens=max_tokens or llm_config.get("max_tokens", 2048),
                    temperature=temperature or llm_config.get("temperature", 0.7),
                    stop=["User:", "\n\n"],
                )
            )
            
            generated_text = result["choices"][0]["text"].strip()
            logger.info(
                "Llama completion generated",
                model=llm_config.get("model"),
                tokens=result["usage"]["total_tokens"]
            )
            return generated_text
        
        except Exception as e:
            logger.error(f"Llama inference error: {e}")
            raise
    
    async def generate_json_completion(
        self,
        prompt: str,
        llm_config: Dict[str, Any],
        system_prompt: Optional[str] = None,
        schema_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from LLM.
        
        Args:
            prompt: User prompt/query
            llm_config: LLM configuration
            system_prompt: Optional system instruction
            schema_hint: Optional JSON schema description
            
        Returns:
            Parsed JSON object
        """
        import json
        
        # Enhance system prompt for JSON output
        json_system_prompt = (system_prompt or "") + "\n\nYou must respond with valid JSON only. No markdown, no explanation."
        if schema_hint:
            json_system_prompt += f"\n\nExpected JSON schema: {schema_hint}"
        
        # Generate completion
        response_text = await self.generate_completion(
            prompt=prompt,
            llm_config=llm_config,
            system_prompt=json_system_prompt,
            temperature=0.3  # Lower temperature for structured output
        )
        
        # Parse JSON from response
        try:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            return json.loads(response_text)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response_text}")
            # Return a fallback structure
            return {"error": "Failed to parse JSON", "raw_response": response_text}


# Global singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
