"""Population profile routes."""
import logging
import json
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..services.public_search import TavilySearchClient
from ..simulation.realistic_population import (
    create_public_evidence_queue,
    EVIDENCE_QUEUE_DIR,
    load_realistic_population,
    refresh_realistic_population_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/population", tags=["population"])


@router.get("/profiles/{profile_id}/preview")
async def preview_population_profile(
    profile_id: str,
    source_path: str | None = None,
    enrich_public_profile: bool = False,
    refresh_cache: bool = False,
):
    """Preview an anonymized realistic population profile."""
    try:
        profile = load_realistic_population(
            profile_id,
            source_path,
            include_public_enrichment=enrich_public_profile,
            refresh_cache=refresh_cache,
        )
        return JSONResponse(content=profile.to_public_dict())
    except Exception as exc:
        logger.exception("Failed to preview population profile %s", profile_id)
        return JSONResponse(content={"error": str(exc)}, status_code=400)


@router.post("/profiles/{profile_id}/refresh")
async def refresh_population_profile(
    profile_id: str,
    source_path: str | None = None,
    enrich_public_profile: bool = False,
):
    """Rebuild the sanitized local cache from the source workbook."""
    try:
        profile = refresh_realistic_population_cache(
            profile_id,
            source_path=source_path,
            include_public_enrichment=enrich_public_profile,
        )
        return JSONResponse(content=profile.to_public_dict())
    except Exception as exc:
        logger.exception("Failed to refresh population profile %s", profile_id)
        return JSONResponse(content={"error": str(exc)}, status_code=400)


@router.post("/profiles/{profile_id}/evidence-queue")
async def build_public_evidence_queue(profile_id: str):
    """Create a manual-review queue for public paper/search evidence."""
    try:
        profile = load_realistic_population(profile_id)
        result = create_public_evidence_queue(profile)
        return JSONResponse(content={"success": True, **result})
    except Exception as exc:
        logger.exception("Failed to build evidence queue for %s", profile_id)
        return JSONResponse(content={"error": str(exc)}, status_code=400)


@router.post("/profiles/{profile_id}/evidence-queue/search")
async def search_public_evidence_candidates(
    profile_id: str,
    agent_id: int | None = None,
    max_results: int = Query(default=3, ge=1, le=10),  # issue #2252: 添加边界检查
):
    """Search public evidence candidates and write them to the review queue."""
    try:
        profile = load_realistic_population(profile_id)
        target_agents = [
            agent for agent in profile.agents
            if agent_id is None or agent.agent_id == agent_id
        ]
        if agent_id is not None and not target_agents:
            return JSONResponse(content={"error": f"Agent not found: {agent_id}"}, status_code=404)

        client = TavilySearchClient()
        queue_path = EVIDENCE_QUEUE_DIR / f"{profile.profile_id}.candidates.json"
        if queue_path.exists():
            with queue_path.open("r", encoding="utf-8") as handle:
                queue = json.load(handle)
        else:
            create_public_evidence_queue(profile)
            with queue_path.open("r", encoding="utf-8") as handle:
                queue = json.load(handle)

        by_id = {item["agent_id"]: item for item in queue.get("agents", [])}
        searched = 0
        for agent in target_agents:
            queries = _fallback_queries(agent.search_queries)
            results = await client.search_with_fallbacks(queries, max_results=max_results)
            by_id[agent.agent_id]["candidates"] = [
                {"title": result.title, "url": result.url, "content": result.content, "score": result.score}
                for result in results
            ]
            searched += 1

        queue["agents"] = list(by_id.values())
        Path(queue_path).parent.mkdir(parents=True, exist_ok=True)
        with queue_path.open("w", encoding="utf-8") as handle:
            json.dump(queue, handle, ensure_ascii=False, indent=2)

        return JSONResponse(content={"success": True, "queue_path": str(queue_path), "searched_agents": searched})
    except Exception as exc:
        logger.exception("Failed to search public evidence for %s", profile_id)
        return JSONResponse(content={"error": str(exc)}, status_code=400)


def _fallback_queries(queries: list[str]) -> list[str]:
    fallbacks = list(queries)
    fallbacks.extend([
        "Shanghai Academy of Social Sciences journalism research papers",
        "Shanghai Academy of Social Sciences Institute of Journalism",
    ])
    return fallbacks
