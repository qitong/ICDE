"""Settings API endpoints for LLM configuration."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import (
    LLMSettingsResponse,
    LLMSettingsUpdate,
    LLMSettingUpdate,
    ProviderConfig,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_llm_service(db: Session = Depends(get_db)) -> LLMService:
    """Dependency to get LLM service instance."""
    return LLMService(db)


# ============== LLM Settings Endpoints ==============

@router.get("/llm", response_model=LLMSettingsResponse)
async def get_llm_settings(
    llm_service: LLMService = Depends(get_llm_service),
):
    """Get all LLM provider settings."""
    providers = llm_service.get_all_settings()
    default_provider = llm_service.get_default_provider()

    return LLMSettingsResponse(
        default_provider=default_provider,
        providers=providers,
    )


@router.put("/llm", response_model=LLMSettingsResponse)
async def update_llm_settings(
    settings: LLMSettingsUpdate,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Update LLM settings for multiple providers."""
    # Update each provider
    for provider_name, provider_settings in settings.providers.items():
        try:
            llm_service.update_setting(
                provider=provider_name,
                api_key=provider_settings.api_key,
                model=provider_settings.model,
                enabled=provider_settings.enabled,
                is_default=provider_settings.is_default,
                api_base_url=provider_settings.api_base_url,
            )
        except Exception as e:
            logger.error(f"Error updating {provider_name}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to update {provider_name}: {str(e)}"
            )

    # Set default provider if specified
    if settings.default_provider:
        llm_service.update_setting(
            provider=settings.default_provider,
            is_default=True,
        )

    # Return updated settings
    providers = llm_service.get_all_settings()
    default_provider = llm_service.get_default_provider()

    return LLMSettingsResponse(
        default_provider=default_provider,
        providers=providers,
    )


@router.put("/llm/{provider}", response_model=ProviderConfig)
async def update_provider_setting(
    provider: str,
    setting: LLMSettingUpdate,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Update settings for a specific LLM provider."""
    try:
        return llm_service.update_setting(
            provider=provider,
            api_key=setting.api_key,
            model=setting.model,
            enabled=setting.enabled,
            is_default=setting.is_default,
            api_base_url=setting.api_base_url,
        )
    except Exception as e:
        logger.error(f"Error updating {provider}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update {provider}: {str(e)}"
        )


@router.post("/llm/{provider}/validate")
async def validate_api_key(
    provider: str,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Validate the API key for a specific provider."""
    try:
        llm_provider = llm_service.get_provider(provider)
        is_valid = await llm_provider.validate_api_key()

        return {
            "provider": provider,
            "valid": is_valid,
            "message": "API key is valid" if is_valid else "API key validation failed",
        }
    except ValueError as e:
        return {
            "provider": provider,
            "valid": False,
            "message": str(e),
        }
    except Exception as e:
        logger.error(f"Validation error for {provider}: {e}")
        return {
            "provider": provider,
            "valid": False,
            "message": f"Validation error: {str(e)}",
        }
