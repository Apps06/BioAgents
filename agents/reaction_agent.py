"""Standalone uAgent wrapper for ``ReactionService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import ReactionRequest, ReactionResponse
from services.reaction_service import ReactionService

agent = Agent(
    name="ReactionAgent",
    seed="reaction_agent_secret",
    port=8004,
    endpoint=["http://localhost:8004/submit"],
)
service = ReactionService()


@agent.on_message(model=ReactionRequest, replies=ReactionResponse)
async def handle_request(ctx: Context, sender: str, msg: ReactionRequest):
    try:
        report = service.simulate_reaction(msg.mol1, msg.mol2)
        await ctx.send(sender, ReactionResponse(status="success", report=report.to_dict()))
    except Exception as exc:
        ctx.logger.error("Reaction simulation failed: %s", exc)
        await ctx.send(sender, ReactionResponse(status="error", error=str(exc)))


if __name__ == "__main__":
    agent.run()
