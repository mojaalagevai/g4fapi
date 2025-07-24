from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security.api_key import APIKeyHeader
from fastapi.openapi.docs import get_swagger_ui_html
import g4f
import time
from typing import Optional, List, Dict, Union
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# Hardcoded supported models and providers
MODEL_PROVIDER_MAP = {
    "gpt-4": ["Blackbox", "PollinationsAI", "Copilot"],
    "gpt-4o": ["Blackbox", "PollinationsAI"],
    "gpt-4o-mini": ["Blackbox", "PollinationsAI"],
    "gpt-4o-mini-audio": ["PollinationsAI"],
    "o1": ["Copilot"],
    "gpt-4.1": ["PollinationsAI"],
    "gpt-4.1-mini": ["Blackbox", "PollinationsAI"],
    "gpt-4.1-nano": ["Blackbox", "PollinationsAI"],
    "dall-e-3": ["Copilot"],
    "llama-2-7b": ["Cloudflare"],
    "llama-2-70b": ["Together"],
    "llama-3-8b": ["Together", "Cloudflare"],
    "llama-3.1-8b": ["Together", "Cloudflare"],
    "llama-3.1-405b": ["Together"],
    "llama-3.2-1b": ["Cloudflare"],
    "llama-3.2-3b": ["Together"],
    "llama-3.2-11b": ["Together"],
    "llama-3.2-90b": ["Together"],
    "llama-3.3-70b": ["PollinationsAI", "Together"],
    "llama-4-scout": ["PollinationsAI", "Together", "Cloudflare"],
    "llama-4-maverick": ["Together"],
    "mistral-7b": ["Together"],
    "mixtral-8x7b": ["Together"],
    "mistral-small-24b": ["Together"],
    "mistral-small-3.1-24b": ["PollinationsAI"],
    "hermes-2-dpo": ["Together"],
    "phi-4": ["PollinationsAI"],
    "gemini-1.5-flash": ["TeachAnything"],
    "gemini-1.5-pro": ["TeachAnything"],
    "gemma-2-27b": ["Together"],
    "blackboxai": ["Blackbox"],
    "qwen-1.5-7b": ["Cloudflare"],
    "qwen-2-72b": ["Together"],
    "qwen-2-vl-72b": ["Together"],
    "qwen-2.5-7b": ["Together"],
    "qwen-2.5-72b": ["Together"],
    "qwen-2.5-coder-32b": ["PollinationsAI", "Together"],
    "qwen-2.5-vl-72b": ["Together"],
    "qwen-3-235b": ["Together"],
    "qwq-32b": ["Together"],
    "deepseek-v3": ["PollinationsAI", "Together"],
    "deepseek-r1": ["Together"],
    "deepseek-r1-distill-qwen-1.5b": ["Together"],
    "deepseek-r1-distill-qwen-14b": ["Together"],
    "deepseek-r1-distill-qwen-32b": ["PollinationsAI"],
    "deepseek-v3-0324": ["PollinationsAI"],
    "grok-3-mini": ["PollinationsAI"],
    "sonar": ["PerplexityLabs"],
    "sonar-pro": ["PerplexityLabs"],
    "sonar-reasoning": ["PerplexityLabs"],
    "sonar-reasoning-pro": ["PerplexityLabs"],
    "r1-1776": ["Together", "PerplexityLabs"],
    "nemotron-70b": ["Together"],
    "evil": ["PollinationsAI"],
    "flux": ["Together"],
    "flux-pro": ["Together"],
    "flux-schnell": ["Together"],
    "flux-kontext-max": ["Together"]
}

# Initialize FastAPI
app = FastAPI(
    title="G4F Proxy API",
    description="Proxy API for G4F models with restricted access to specific models and providers.",
    version="1.0",
    docs_url=None,
    redoc_url="/redoc"
)

# Serve custom Swagger UI at /docs
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="G4F Proxy API Docs")

# Define API Key Security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
valid_api_keys = {"123456", "marufking"}  # Initial keys; add more later

# Dependency for API Key Auth
def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if api_key not in valid_api_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


# Pydantic Models
class ChatRequest(BaseModel):
    model: str
    provider: Optional[str] = None
    messages: List[Dict[str, str]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False

    class Config:
        schema_extra = {
            "example": {
                "model": "gpt-4o-mini",
                "provider": "PollinationsAI",
                "messages": [
                    {"role": "user", "content": "What is AI?"}
                ]
            }
        }


@app.post("/chat", summary="Chat with a G4F-supported model", dependencies=[Depends(get_api_key)])
async def chat(request: ChatRequest = Body(...)):
    """
    Send a chat request to one of the supported G4F models.

    Optionally specify a provider to force a particular backend.

    ### Example Request:
    ```json
    {
      "model": "gpt-4o-mini",
      "provider": "PollinationsAI",
      "messages": [
        {"role": "user", "content": "What is AI?"}
      ]
    }
    ```

    ### Response:
    Returns generated text and processing time in seconds.
    ```json
    {
      "response": "Artificial Intelligence (AI) refers to...",
      "process_time": "0.87"
    }
    """
    if request.model not in MODEL_PROVIDER_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' is not supported."
        )

    available_providers = MODEL_PROVIDER_MAP[request.model]
    selected_provider = None

    if request.provider:
        if request.provider not in available_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{request.provider}' does not support model '{request.model}'. "
                       f"Available providers: {', '.join(available_providers)}"
            )
        selected_provider = getattr(g4f.Provider, request.provider, None)
        if not selected_provider:
            raise HTTPException(status_code=400, detail=f"G4F Provider '{request.provider}' not found.")

    try:
        start_time = time.time()
        response = await g4f.ChatCompletion.create_async(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
            provider=selected_provider if selected_provider else None
        )
        process_time = round(time.time() - start_time, 2)

        return JSONResponse(content={"response": response, "process_time": process_time})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models", summary="List All Supported Models and Providers", dependencies=[Depends(get_api_key)])
async def list_models():
    """
    Returns a dictionary where each key is a model name, and the value is a list of available providers for that model.
    """
    return {"models": MODEL_PROVIDER_MAP}


# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)