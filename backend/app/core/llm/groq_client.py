"""
Groq LLM Client
Manages Groq API calls with model rotation, retry logic, and fallback mechanisms
"""

import logging
import random
import re
from typing import Optional, List, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def clean_llm_response(text: str) -> str:
    """
    Clean LLM response by removing thinking tags and other artifacts.
    Strips <think>...</think> blocks that some models output.
    """
    if not text:
        return text
    
    # Remove <think>...</think> blocks (including multiline)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining orphaned tags
    cleaned = re.sub(r'</?think>', '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


class GroqClientError(Exception):
    """Custom exception for Groq client errors"""
    pass


class GroqClient:
    """
    Groq LLM client with:
    - Random model selection from pool for load distribution
    - Retry logic with exponential backoff
    - Fallback to next model on failure
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.models = self.settings.groq_models.copy()
        self._current_model_index = 0
    
    def _get_random_model(self) -> str:
        """Select a random model from the pool"""
        return random.choice(self.models)
    
    def _get_next_fallback_model(self, current: str) -> Optional[str]:
        """Get next model in rotation for fallback"""
        try:
            current_idx = self.models.index(current)
            next_idx = (current_idx + 1) % len(self.models)
            return self.models[next_idx]
        except ValueError:
            return self.models[0] if self.models else None
    
    def _create_chat_model(self, model_name: str) -> ChatGroq:
        """Create a ChatGroq instance for the specified model"""
        return ChatGroq(
            groq_api_key=self.settings.groq_api_key,
            model_name=model_name,
            temperature=0.1,
            max_tokens=4096
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _invoke_with_retry(
        self, 
        model: ChatGroq, 
        messages: List[BaseMessage]
    ) -> AIMessage:
        """Invoke model with retry logic"""
        response = await model.ainvoke(messages)
        return response
    
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke the LLM with messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            model_name: Optional specific model to use (otherwise random)
        
        Returns:
            Dict with 'content', 'model_used', and 'success'
        """
        # Select model
        selected_model = model_name or self._get_random_model()
        models_tried = set()
        
        # Convert messages to LangChain format
        lc_messages: List[BaseMessage] = []
        
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
        
        # Try models with fallback
        while len(models_tried) < len(self.models):
            models_tried.add(selected_model)
            
            try:
                logger.info(f"Invoking Groq model: {selected_model}")
                chat_model = self._create_chat_model(selected_model)
                response = await self._invoke_with_retry(chat_model, lc_messages)
                
                return {
                    "content": clean_llm_response(response.content),
                    "model_used": selected_model,
                    "success": True
                }
                
            except Exception as e:
                logger.warning(f"Model {selected_model} failed: {e}")
                next_model = self._get_next_fallback_model(selected_model)
                
                if next_model and next_model not in models_tried:
                    logger.info(f"Falling back to model: {next_model}")
                    selected_model = next_model
                else:
                    raise GroqClientError(f"All models failed. Last error: {e}")
        
        raise GroqClientError("No available models to try")
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Stream responses from the LLM.
        Yields content chunks as they arrive.
        """
        selected_model = model_name or self._get_random_model()
        
        lc_messages: List[BaseMessage] = []
        
        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
        
        chat_model = self._create_chat_model(selected_model)
        
        async for chunk in chat_model.astream(lc_messages):
            if chunk.content:
                yield {
                    "content": chunk.content,
                    "model_used": selected_model
                }


# Global client instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create Groq client instance"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
