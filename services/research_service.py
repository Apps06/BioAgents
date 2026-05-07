"""Discovery query service."""

from __future__ import annotations

from knowledge.metta_handler import get_kb
from models.molecule import CandidateCompound, DiscoveryResult
from services.base_service import BioAgentService, ServiceIdentity


class ResearchService(BioAgentService):
    identity = ServiceIdentity("ResearchAgent", "research_agent_secret", 8005)

    def discover(
        self,
        *,
        target_class: str | None = None,
        similar_to: str | None = None,
        min_activity: float | None = None,
        min_selectivity: float | None = None,
    ) -> DiscoveryResult:
        kb = get_kb()
        candidates = kb.get_all_candidates()

        similar_set: set[str] | None = None
        if similar_to:
            similar_set = set(kb.get_similar(similar_to))

        filtered = [
            candidate
            for candidate in candidates
            if self._matches(
                candidate,
                target_class=target_class,
                similar_set=similar_set,
                min_activity=min_activity,
                min_selectivity=min_selectivity,
            )
        ]

        query = {
            "target_class": target_class,
            "similar_to": kb.resolve_name(similar_to) if similar_to else None,
            "min_activity": min_activity,
            "min_selectivity": min_selectivity,
        }
        return DiscoveryResult(query=query, count=len(filtered), candidates=filtered)

    @staticmethod
    def _matches(
        candidate: CandidateCompound,
        *,
        target_class: str | None,
        similar_set: set[str] | None,
        min_activity: float | None,
        min_selectivity: float | None,
    ) -> bool:
        props = candidate.properties
        if target_class and target_class not in props.categories:
            return False
        if similar_set is not None and candidate.molecule not in similar_set:
            return False
        if min_activity is not None and (props.activity_score is None or props.activity_score < min_activity):
            return False
        if min_selectivity is not None and (props.selectivity is None or props.selectivity < min_selectivity):
            return False
        return True
