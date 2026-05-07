"""Ranking and summary statistics for discovery results."""

from __future__ import annotations

from statistics import mean, median

from exceptions import InvalidInputError
from models.molecule import CandidateCompound, DiscoveryResult, RankedResult, RankingStats
from services.base_service import BioAgentService, ServiceIdentity


class AnalysisService(BioAgentService):
    identity = ServiceIdentity("AnalysisAgent", "analysis_agent_secret", 8006)

    _ALLOWED_CRITERIA = {"activity_score", "selectivity", "stability_h", "molecular_weight"}

    def rank(
        self,
        discovery: DiscoveryResult,
        *,
        criterion: str = "activity_score",
        ascending: bool = False,
    ) -> RankedResult:
        if criterion not in self._ALLOWED_CRITERIA:
            allowed = ", ".join(sorted(self._ALLOWED_CRITERIA))
            raise InvalidInputError(f"Unknown ranking criterion '{criterion}'. Expected one of: {allowed}.")

        scored: list[tuple[float, CandidateCompound]] = []
        skipped: list[str] = []
        for candidate in discovery.candidates:
            value = getattr(candidate.properties, criterion)
            if value is None:
                skipped.append(candidate.molecule)
                continue
            scored.append((float(value), candidate))

        scored.sort(key=lambda item: item[0], reverse=not ascending)
        scores = [item[0] for item in scored]
        stats = RankingStats(
            minimum=min(scores) if scores else 0.0,
            maximum=max(scores) if scores else 0.0,
            mean=mean(scores) if scores else 0.0,
            median=median(scores) if scores else 0.0,
        )

        return RankedResult(
            criterion=criterion,
            sort_order="ascending" if ascending else "descending",
            count=len(scored),
            skipped=skipped,
            stats=stats,
            ranked_candidates=[candidate for _, candidate in scored],
        )
