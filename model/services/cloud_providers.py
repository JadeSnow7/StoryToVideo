"""Cloud provider adapters for StoryToVideo model services.

This module provides a unified interface for switching between local and cloud-based
AI model providers for LLM, text-to-image, TTS, and image-to-video services.

Supported providers:
- LLM: Groq (free tier), DeepSeek, OpenRouter, Ollama (local)
- Text-to-Image: AI Horde (free), Cloudflare Workers AI, SD Turbo (local)
- TTS: ElevenLabs, Azure Speech, CosyVoice (local)
- Image-to-Video: SVD (local only, optimized)
"""

import asyncio
import base64
import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx


# =============================================================================
# Provider Enums
# =============================================================================

class LLMProvider(str, Enum):
    """Available LLM providers."""
    OLLAMA = "ollama"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"


class ImageProvider(str, Enum):
    """Available text-to-image providers."""
    LOCAL = "local"
    AI_HORDE = "horde"
    CLOUDFLARE = "cloudflare"


class TTSProvider(str, Enum):
    """Available TTS providers."""
    LOCAL = "local"
    ELEVENLABS = "elevenlabs"
    AZURE = "azure"
    EDGE_TTS = "edge"


# =============================================================================
# Configuration
# =============================================================================

def get_provider_config() -> Dict[str, str]:
    """Get provider configuration from environment variables."""
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "image_provider": os.getenv("IMAGE_PROVIDER", "local"),
        "tts_provider": os.getenv("TTS_PROVIDER", "local"),
        # API Keys
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "cloudflare_account_id": os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
        "cloudflare_api_token": os.getenv("CLOUDFLARE_API_TOKEN", ""),
        "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
        "azure_speech_key": os.getenv("AZURE_SPEECH_KEY", ""),
        "azure_speech_region": os.getenv("AZURE_SPEECH_REGION", "eastasia"),
    }


# =============================================================================
# Base Provider Classes
# =============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        pass


class BaseImageProvider(ABC):
    """Abstract base class for text-to-image providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 384,
    ) -> bytes:
        """Generate an image from text prompt. Returns image bytes (PNG)."""
        pass


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, int]:
        """Synthesize speech from text. Returns (audio_bytes, sample_rate)."""
        pass


# =============================================================================
# LLM Providers
# =============================================================================

class GroqProvider(BaseLLMProvider):
    """Groq LLM provider with free tier support."""
    
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.1-70b-versatile"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM provider with free tier."""
    
    BASE_URL = "https://api.deepseek.com/v1/chat/completions"
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider for accessing multiple LLMs."""
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "meta-llama/llama-3.1-70b-instruct:free"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/JadeSnow7/StoryToVideo",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


# =============================================================================
# Image Providers
# =============================================================================

class AIHordeProvider(BaseImageProvider):
    """AI Horde (Stable Horde) - completely free, community-driven."""
    
    BASE_URL = "https://stablehorde.net/api/v2"
    ANONYMOUS_KEY = "0000000000"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self.ANONYMOUS_KEY
        
    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 384,
    ) -> bytes:
        # Ensure dimensions are valid (multiple of 64 for SD)
        width = (width // 64) * 64
        height = (height // 64) * 64
        
        payload = {
            "prompt": prompt,
            "params": {
                "width": max(width, 256),
                "height": max(height, 256),
                "steps": 20,
                "cfg_scale": 7.0,
            },
            "nsfw": False,
            "censor_nsfw": True,
            "models": ["stable_diffusion"],
        }
        if negative_prompt:
            payload["params"]["negative_prompt"] = negative_prompt
            
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Submit generation request
            submit_resp = await client.post(
                f"{self.BASE_URL}/generate/async",
                headers={"apikey": self.api_key},
                json=payload,
            )
            submit_resp.raise_for_status()
            job_id = submit_resp.json()["id"]
            
            # Poll for completion
            max_attempts = 60
            for _ in range(max_attempts):
                check_resp = await client.get(
                    f"{self.BASE_URL}/generate/check/{job_id}"
                )
                check_data = check_resp.json()
                
                if check_data.get("done"):
                    # Get result
                    result_resp = await client.get(
                        f"{self.BASE_URL}/generate/status/{job_id}"
                    )
                    result_data = result_resp.json()
                    generations = result_data.get("generations", [])
                    if generations:
                        img_b64 = generations[0].get("img", "")
                        return base64.b64decode(img_b64)
                    raise RuntimeError("AI Horde returned empty generation")
                    
                await asyncio.sleep(5)
                
            raise TimeoutError("AI Horde generation timed out")


class CloudflareProvider(BaseImageProvider):
    """Cloudflare Workers AI - fast, with generous free tier."""
    
    URL_TEMPLATE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
    
    def __init__(self, account_id: str, api_token: str):
        self.account_id = account_id
        self.api_token = api_token
        self.url = self.URL_TEMPLATE.format(account_id=account_id)
        
    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 384,
    ) -> bytes:
        payload = {"prompt": prompt}
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.content  # Returns PNG image bytes


# =============================================================================
# TTS Providers
# =============================================================================

class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs TTS - high quality, 10k chars/month free."""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    DEFAULT_MODEL = "eleven_multilingual_v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, int]:
        voice_id = voice or self.DEFAULT_VOICE
        
        payload = {
            "text": text,
            "model_id": self.DEFAULT_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            # ElevenLabs returns mp3 at 44100 Hz
            return resp.content, 44100


class EdgeTTSProvider(BaseTTSProvider):
    """Microsoft Edge TTS - completely free, good quality."""
    
    def __init__(self):
        pass  # No API key needed
        
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bytes, int]:
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts not installed. Run: pip install edge-tts")
            
        voice = voice or "zh-CN-XiaoxiaoNeural"
        rate = f"+{int((speed - 1) * 100)}%" if speed >= 1 else f"{int((speed - 1) * 100)}%"
        
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
                
        return audio_bytes, 24000  # Edge TTS outputs at 24kHz


# =============================================================================
# Provider Factory
# =============================================================================

def get_llm_provider(config: Optional[Dict] = None) -> BaseLLMProvider:
    """Get the configured LLM provider instance."""
    config = config or get_provider_config()
    provider = config["llm_provider"].lower()
    
    if provider == LLMProvider.GROQ:
        api_key = config["groq_api_key"]
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        return GroqProvider(api_key)
    elif provider == LLMProvider.DEEPSEEK:
        api_key = config["deepseek_api_key"]
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        return DeepSeekProvider(api_key)
    elif provider == LLMProvider.OPENROUTER:
        api_key = config["openrouter_api_key"]
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        return OpenRouterProvider(api_key)
    else:
        # Default to ollama - handled by existing code
        return None


def get_image_provider(config: Optional[Dict] = None) -> BaseImageProvider:
    """Get the configured image provider instance."""
    config = config or get_provider_config()
    provider = config["image_provider"].lower()
    
    if provider == ImageProvider.AI_HORDE:
        return AIHordeProvider()
    elif provider == ImageProvider.CLOUDFLARE:
        account_id = config["cloudflare_account_id"]
        api_token = config["cloudflare_api_token"]
        if not account_id or not api_token:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN required")
        return CloudflareProvider(account_id, api_token)
    else:
        # Default to local - handled by existing code
        return None


def get_tts_provider(config: Optional[Dict] = None) -> BaseTTSProvider:
    """Get the configured TTS provider instance."""
    config = config or get_provider_config()
    provider = config["tts_provider"].lower()
    
    if provider == TTSProvider.ELEVENLABS:
        api_key = config["elevenlabs_api_key"]
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        return ElevenLabsProvider(api_key)
    elif provider == TTSProvider.EDGE_TTS or provider == TTSProvider.AZURE:
        # Edge TTS is free and doesn't need Azure credentials
        return EdgeTTSProvider()
    else:
        # Default to local - handled by existing code
        return None
