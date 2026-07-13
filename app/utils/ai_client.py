import httpx
from fastapi import HTTPException, status
from loguru import logger

from app.config.settings import AI

ai_config = AI()


async def call_ai(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 10000,
    service_name: str = "AI",
) -> str:
    """Call external AI API and return response content.

    Args:
        prompt (str): The user prompt to send to the AI API.
        system_prompt (str, optional): An optional system prompt to provide context. Defaults to "".
        temperature (float, optional): Sampling temperature for response generation. Defaults to 0.1.
        max_tokens (int, optional): Maximum number of tokens in the response. Defaults to 10000.
        service_name (str, optional): Name of the AI service for error messages. Defaults to "AI".

    Raises:
        HTTPException 503 if API key missing or unreachable.
        HTTPException 502 if API returns error or unexpected response.
    """
    if not ai_config.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI {service_name} service not configured",
        )

    messages = [{"role": "user", "content": prompt}]
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(
                ai_config.api_url,
                headers={
                    "Authorization": f"Bearer {ai_config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ai_config.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

        if response.status_code != status.HTTP_200_OK:
            logger.error(f"AI API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI {service_name} service returned an error",
            )

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except httpx.RequestError as e:
        logger.error(f"AI API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI {service_name} service unavailable",
        )
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Unexpected AI API response structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI {service_name} returned unexpected response format",
        )
