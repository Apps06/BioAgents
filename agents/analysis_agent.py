"""Standalone uAgent wrapper for ``AnalysisService``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import AnalysisRequest, AnalysisResponse
from models.molecule import CandidateCompound, DiscoveryResult, MoleculeProperties
from services.analysis_service import AnalysisService

agent = Agent(
    name="AnalysisAgent",
    seed="analysis_agent_secret",
    port=8006,
    endpoint=["http://localhost:8006/submit"],
)
service = AnalysisService()


@agent.on_message(model=AnalysisRequest, replies=AnalysisResponse)
async def handle_request(ctx: Context, sender: str, msg: AnalysisRequest):
    try:
        discovery = _discovery_from_dict(msg.discovery_data)
        ranked = service.rank(
            discovery,
            criterion=msg.criterion,
            ascending=msg.ascending,
        )
        await ctx.send(sender, AnalysisResponse(status="success", analysis=ranked.to_dict()))
    except Exception as exc:
        ctx.logger.error("Analysis failed: %s", exc)
        await ctx.send(sender, AnalysisResponse(status="error", error=str(exc)))


def _discovery_from_dict(data: dict[str, Any]) -> DiscoveryResult:
    candidates = []
    for item in data.get("candidates", []):
        props = MoleculeProperties(**item["properties"])
        candidates.append(CandidateCompound(molecule=item["molecule"], properties=props))
    return DiscoveryResult(
        query=data.get("query", {}),
        count=data.get("count", len(candidates)),
        candidates=candidates,
    )


if __name__ == "__main__":
    agent.run()
