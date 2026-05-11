# online_ai_provider.py
"""
Online AI Provider - Adds internet-based AI to ai_widget_lite
Just add this file and modify ai_widget_lite slightly

FREE APIs supported:
- Groq (fast, free tier)
- Hugging Face Inference
- OpenAI (requires API key)
- Anthropic Claude (requires API key)

Install: pip install requests
"""
import requests
import json
from PyQt5.QtCore import QThread, pyqtSignal


class OnlineAIProvider:
    """Manages online AI API calls"""
    def __init__(self):
        self.provider = "groq"  # Default: groq (fast + free)
        self.api_key = None
        self.model = None
        self.available_providers = {
            "groq": {
                "name": "Groq (Fast & Free)",
                "requires_key": True,
                "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"],
                "free": True,
                "speed": "Very Fast"
            },
            "qwen": {
                "name": "Qwen (Alibaba Cloud)",
                "requires_key": True,
                "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
                "free": False,
                "speed": "Fast"
            },
            "deepseek": {
                "name": "DeepSeek",
                "requires_key": True,
                "models": ["deepseek-chat", "deepseek-coder"],
                "free": False,
                "speed": "Fast"
            },
            "openai": {
                "name": "OpenAI ChatGPT",
                "requires_key": True,
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"],
                "free": False,
                "speed": "Fast"
            },
            "huggingface": {
                "name": "Hugging Face",
                "requires_key": False,
                "models": ["microsoft/DialoGPT-large", "google/flan-t5-xxl"],
                "free": True,
                "speed": "Slow"
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "requires_key": True,
                "models": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
                "free": False,
                "speed": "Fast"
            }
        }
    
    def set_provider(self, provider, api_key=None, model=None):
        """Set the AI provider"""
        if provider not in self.available_providers:
            return False
        
        self.provider = provider
        self.api_key = api_key
        
        if model:
            self.model = model
        else:
            # Use first available model
            self.model = self.available_providers[provider]["models"][0]
        
        return True
    
    def is_configured(self):
        """Check if provider is properly configured"""
        provider_info = self.available_providers[self.provider]
        if provider_info["requires_key"] and not self.api_key:
            return False
        return True
    
    def query(self, prompt, max_tokens=512, temperature=0.7):
        """Query the selected AI provider"""
        if not self.is_configured():
            return None, "API key required. Please configure in settings."
        
        try:
            if self.provider == "groq":
                return self._query_groq(prompt, max_tokens, temperature)
            elif self.provider == "qwen":
                return self._query_qwen(prompt, max_tokens, temperature)
            elif self.provider == "deepseek":
                return self._query_deepseek(prompt, max_tokens, temperature)
            elif self.provider == "openai":
                return self._query_openai(prompt, max_tokens, temperature)
            elif self.provider == "huggingface":
                return self._query_huggingface(prompt, max_tokens)
            elif self.provider == "anthropic":
                return self._query_anthropic(prompt, max_tokens, temperature)
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def _query_groq(self, prompt, max_tokens, temperature):
        """Query Groq API (Fast & Free)"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"], None
        else:
            return None, f"API Error: {response.status_code}"

    def _query_qwen(self, prompt, max_tokens, temperature):
        """Query Qwen API (Alibaba Cloud)"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "input": {
                "messages": [{"role": "user", "content": prompt}]
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["output"]["choices"][0]["message"]["content"], None
        else:
            return None, f"API Error: {response.status_code}"

    def _query_deepseek(self, prompt, max_tokens, temperature):
        """Query DeepSeek API"""
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"], None
        else:
            return None, f"API Error: {response.status_code}"
            
    
    def _query_huggingface(self, prompt, max_tokens):
        """Query Hugging Face Inference API (Free, no key needed)"""
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Content-Type": "application/json"}
        
        # Add API key if available for better rate limits
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "return_full_text": False
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", ""), None
            return str(result), None
        else:
            return None, f"API Error: {response.status_code}"
    
    def _query_openai(self, prompt, max_tokens, temperature):
        """Query OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"], None
        else:
            return None, f"API Error: {response.status_code}"
    
    def _query_anthropic(self, prompt, max_tokens, temperature):
        """Query Anthropic Claude API"""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"], None
        else:
            return None, f"API Error: {response.status_code}"


class OnlineAIThread(QThread):
    """Background thread for online AI queries"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, provider, prompt, max_tokens=512, temperature=0.7):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def run(self):
        """Run query in background"""
        response, error = self.provider.query(
            self.prompt, 
            self.max_tokens, 
            self.temperature
        )
        
        if error:
            self.error_occurred.emit(error)
        else:
            self.response_ready.emit(response)
