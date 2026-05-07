"""Standalone uAgent wrapper for ``ResearchService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import ResearchRequest, ResearchResponse
from services.research_service import ResearchService

agent = Agent(
    name="ResearchAgent",
    seed="research_agent_secret",
    port=8005,
    endpoint=["http://localhost:8005/submit"],
)
service = ResearchService()


@agent.on_message(model=ResearchRequest, replies=ResearchResponse)
async def handle_request(ctx: Context, sender: str, msg: ResearchRequest):
    try:
        discovery = service.discover(
            target_class=msg.target_class,
            similar_to=msg.similar_to,
            min_activity=msg.min_activity,
            min_selectivity=msg.min_selectivity,
        )
        await ctx.send(sender, ResearchResponse(status="success", discovery=discovery.to_dict()))
    except Exception as exc:
        ctx.logger.error("Discovery failed: %s", exc)
        await ctx.send(sender, ResearchResponse(status="error", error=str(exc)))


if __name__ == "__main__":
    agent.run()
