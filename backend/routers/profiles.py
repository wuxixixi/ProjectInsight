"""User-defined offline population profile routes."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ..simulation.realistic_population import (
    build_user_defined_population_profile,
    get_available_realistic_profiles,
    get_user_profile_source_dir,
    normalize_profile_id,
    save_user_profile_sources,
    update_user_profile_meta,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
async def list_profiles():
    """List built-in and user-defined reusable population profiles."""
    return {"success": True, "profiles": get_available_realistic_profiles()}


@router.post("/upload")
async def upload_profile_sources(
    profile_id: str = Form(...),
    display_name: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    """Store source files for an offline user-defined profile."""
    try:
        normalized = normalize_profile_id(profile_id)
        file_payloads = []
        for upload in files:
            content = await upload.read()
            file_payloads.append((upload.filename or "source.dat", content))
        result = save_user_profile_sources(normalized, file_payloads)
        if display_name:
            update_user_profile_meta(normalized, display_name=display_name)
        return {"success": True, **result}
    except Exception as exc:
        logger.error(f"Profile source upload failed: {exc}")
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=400)


@router.post("/build")
async def build_profile(data: dict):
    """Build or rebuild a reusable offline profile cache from stored sources."""
    try:
        profile_id = normalize_profile_id(str(data.get("profile_id", "")))
        display_name = data.get("display_name") or profile_id
        source_path = data.get("source_path") or str(get_user_profile_source_dir(profile_id))
        profile = build_user_defined_population_profile(
            profile_id,
            source_path=source_path,
            display_name=display_name,
            refresh_cache=True,
        )
        return {"success": True, "profile": profile.to_public_dict()}
    except Exception as exc:
        logger.error(f"Profile build failed: {exc}")
        return JSONResponse(content={"success": False, "error": str(exc)}, status_code=400)
