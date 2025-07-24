# (Uploaded [file](Pasted_Text_1753390692491.txt)) 
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
# According to Clever Cloud docs, the app should listen on port 9000
# We'll make the host and port configurable via environment variables, defaulting to 0.0.0.0:9000
import os

host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", 9000)) # Clever Cloud expects the app to listen on the PORT env var

app = FastAPI(
    title="G4F Proxy API",
    description="Proxy API for G4F models with restricted access to specific models and providers.",
    version="1.0",
    docs_url=None, # Disable default docs
    redoc_url="/redoc" # Keep ReDoc at /redoc
)

# Serve custom Swagger UI at /docs
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="G4F Proxy API Docs")

# Define API Key Security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
# Consider using an environment variable for API keys in production
# valid_api_keys_str = os.getenv("VALID_API_KEYS", "123456,marufking") # Comma-separated string
# valid_api_keys = set(key.strip() for key in valid_api_keys_str.split(","))
# For now, keeping the hardcoded keys as in the original, but recommend the above approach.
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

        # Ensure response is a string. g4f might return a generator for streaming.
        # This simple proxy assumes non-streaming responses for the JSON output.
        if isinstance(response, str):
            final_response = response
        elif hasattr(response, '__aiter__'): # Likely an async generator for streaming
            # For simplicity in this proxy, we'll consume the stream and return the full text.
            # A full streaming proxy would need a different approach (e.g., Server-Sent Events).
             # Warning: This consumes the entire stream before responding.
            chunks = []
            async for chunk in response:
                 chunks.append(chunk)
            final_response = "".join(chunks)
        else:
             final_response = str(response) # Fallback

        return JSONResponse(content={"response": final_response, "process_time": process_time})
    except Exception as e:
        # Log the exception for debugging (consider using Python's logging module)
        print(f"Error during chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models", summary="List All Supported Models and Providers", dependencies=[Depends(get_api_key)])
async def list_models():
    """
    Returns a dictionary where each key is a model name, and the value is a list of available providers for that model.
    """
    return {"models": MODEL_PROVIDER_MAP}


# Run the server using uvicorn when the script is executed directly.
# Clever Cloud prefers using CC_RUN_COMMAND or standard Python module execution.
# However, if running directly (e.g., `python main.py`), this block will use uvicorn.
# Ensure `uvicorn` is in your requirements.txt.
# According to Clever Cloud docs, you could also use CC_RUN_COMMAND="uvicorn main:app --host 0.0.0.0 --port $PORT"
# in the environment variables instead of this if __name__ block.
if __name__ == "__main__":
    import uvicorn
    # Use the host and port determined from environment variables or defaults
    uvicorn.run(app, host=host, port=port)
