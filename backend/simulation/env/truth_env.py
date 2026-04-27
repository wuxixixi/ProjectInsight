"""
TruthEnv - official truth intervention environment.
"""
from typing import Dict, List, Any, Optional
import logging
import numpy as np

from .base import EnvBase, tool

logger = logging.getLogger(__name__)


class Intervention:
    """Official intervention event."""

    _next_id: int = 0

    def __init__(
        self,
        step: int,
        content: str,
        credibility: float = 0.7,
        reach: float = 1.0,
        timing: str = "delayed"
    ):
        Intervention._next_id += 1
        self.id = Intervention._next_id
        self.step = step
        self.content = content
        self.credibility = credibility
        self.reach = reach
        self.timing = timing
        self.active = True
        self.exposure_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step": self.step,
            "content": self.content,
            "credibility": self.credibility,
            "reach": self.reach,
            "timing": self.timing,
            "active": self.active,
            "exposure_count": self.exposure_count,
        }


class TruthEnv(EnvBase):
    """Manage publication and exposure of truth interventions."""

    def __init__(
        self,
        response_delay: int = 10,
        default_credibility: float = 0.7,
        seed: int = 42
    ):
        super().__init__()
        self._response_delay = response_delay
        self._default_credibility = default_credibility
        self._interventions: List[Intervention] = []
        self._published: List[Intervention] = []
        self._exposure_tracking: Dict[int, set] = {}
        self._current_step = 0
        self._rng = np.random.default_rng(seed)

    @property
    def name(self) -> str:
        return "truth"

    def get_intervention_sync(self, agent_id: int) -> Optional[str]:
        """Synchronous wrapper for the sync engine path."""
        for intervention in self._published:
            if not intervention.active:
                continue

            derived_seed = int(
                self._rng.integers(0, 2**31) + agent_id + self._current_step * 1000
            ) % (2**31)
            agent_rng = np.random.default_rng(derived_seed)
            if agent_rng.random() < intervention.reach:
                if agent_id not in self._exposure_tracking:
                    self._exposure_tracking[agent_id] = set()
                self._exposure_tracking[agent_id].add(intervention.id)
                intervention.exposure_count += 1
                return intervention.content

        return None

    def add_intervention_sync(
        self,
        content: str,
        step: Optional[int] = None,
        credibility: Optional[float] = None,
        reach: float = 1.0,
        timing: str = "delayed"
    ):
        """Synchronous wrapper for the sync engine path."""
        if step is None:
            step = self._current_step + self._response_delay

        intervention = Intervention(
            step=step,
            content=content,
            credibility=credibility or self._default_credibility,
            reach=reach,
            timing=timing,
        )
        self._interventions.append(intervention)
        if intervention.step <= self._current_step and intervention not in self._published:
            self._published.append(intervention)

    @tool(readonly=True, kind="observe")
    async def get_intervention(self, agent_id: int) -> Optional[str]:
        return self.get_intervention_sync(agent_id)

    @tool(readonly=True, kind="observe")
    async def get_credibility(self) -> float:
        return self._default_credibility

    @tool(readonly=True, kind="statistics")
    async def get_intervention_stats(self) -> Dict[str, Any]:
        return {
            "total_interventions": len(self._interventions),
            "published_interventions": len(self._published),
            "pending_interventions": len(self._interventions) - len(self._published),
            "total_exposure": sum(len(exposures) for exposures in self._exposure_tracking.values()),
            "agents_reached": len(self._exposure_tracking),
        }

    @tool(readonly=True, kind="statistics")
    async def get_timing_analysis(self) -> Dict[str, Any]:
        if not self._published:
            return {"avg_delay": 0, "timing_categories": {}}

        delays = [i.step for i in self._published]
        timing_categories: Dict[str, int] = {}
        for intervention in self._published:
            timing_categories[intervention.timing] = timing_categories.get(intervention.timing, 0) + 1

        return {
            "avg_delay": sum(delays) / len(delays),
            "earliest": min(delays),
            "latest": max(delays),
            "timing_categories": timing_categories,
        }

    @tool(readonly=False, kind="interact")
    async def add_intervention(
        self,
        content: str,
        step: Optional[int] = None,
        credibility: Optional[float] = None,
        reach: float = 1.0,
        timing: str = "delayed"
    ):
        self.add_intervention_sync(
            content=content,
            step=step,
            credibility=credibility,
            reach=reach,
            timing=timing,
        )

    @tool(readonly=False, kind="interact")
    async def set_credibility(self, credibility: float):
        self._default_credibility = max(0.0, min(1.0, credibility))

    def advance_step(self, step: int):
        self._current_step = step
        for intervention in self._interventions:
            if intervention not in self._published and intervention.step <= step:
                self._published.append(intervention)
                logger.info(
                    "TruthEnv: step %s published intervention - %s...",
                    step,
                    intervention.content[:30],
                )

    async def reset(self):
        self._interventions.clear()
        self._published.clear()
        self._exposure_tracking.clear()
        self._current_step = 0

    async def get_state(self) -> Dict[str, Any]:
        return {
            "current_step": self._current_step,
            "pending_interventions": len(self._interventions) - len(self._published),
            "published_count": len(self._published),
            "default_credibility": self._default_credibility,
        }
