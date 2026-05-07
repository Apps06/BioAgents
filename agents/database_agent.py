"""Standalone uAgent wrapper for ``DatabaseService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import LookupRequest, LookupResponse
from services.database_service import DatabaseService

agent = Agent(
    name="DatabaseAgent",
    seed="db_agent_secret",
    port=8003,
    endpoint=["http://localhost:8003/submit"],
)
service = DatabaseService()


@agent.on_message(model=LookupRequest, replies=LookupResponse)
async def handle_request(ctx: Context, sender: str, msg: LookupRequest):
    try:
        compound = service.fetch_pubchem(msg.query)
        await ctx.send(sender, LookupResponse(status="success", compound=compound.to_dict()))
    except Exception as exc:
        ctx.logger.error("PubChem lookup failed: %s", exc)
        await ctx.send(sender, LookupResponse(status="error", error=str(exc)))


if __name__ == "__main__":
    agent.run()
