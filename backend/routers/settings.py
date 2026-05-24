"""
System settings routes.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config.runtime_settings import get_effective_llm_settings, save_runtime_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/llm")
async def get_llm_settings():
    return {
        "success": True,
        "data": get_effective_llm_settings(),
    }


@router.post("/llm")
async def update_llm_settings(payload: dict):
    try:
        settings = save_runtime_settings(payload)
    except OSError as exc:
        return JSONResponse(
            content={"success": False, "error": f"设置保存失败: {exc}"},
            status_code=500,
        )

    return {
        "success": True,
        "data": settings,
    }
