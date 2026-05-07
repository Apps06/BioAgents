"""Standalone uAgent wrapper for ``CompoundService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import CompoundRequest, CompoundResponse
from services.compound_service import CompoundService

agent = Agent(
    name="CompoundAgent",
    seed="compound_agent_secret",
    port=8002,
    endpoint=["http://localhost:8002/submit"],
)
service = CompoundService()


@agent.on_message(model=CompoundRequest, replies=CompoundResponse)
async def handle_request(ctx: Context, sender: str, msg: CompoundRequest):
    try:
        profile = service.get_profile(msg.molecule)
        await ctx.send(sender, CompoundResponse(status="success", profile=profile.to_dict()))
    except Exception as exc:
        ctx.logger.error("Compound lookup failed: %s", exc)
        await ctx.send(sender, CompoundResponse(status="error", error=str(exc)))


if __name__ == "__main__":
    agent.run()
