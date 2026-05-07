"""Standalone uAgent wrapper for ``LLMService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMInsightRequest,
    LLMInsightResponse,
)
from services.llm_service import LLMService

agent = Agent(
    name="LLMAgent",
    seed="llm_agent_secret",
    port=8007,
    endpoint=["http://localhost:8007/submit"],
)
service = LLMService()


@agent.on_message(model=LLMInsightRequest, replies=LLMInsightResponse)
async def handle_insight_request(ctx: Context, sender: str, msg: LLMInsightRequest):
    try:
        insight = service.generate_insight(msg.context_type, msg.data) or ""
        await ctx.send(sender, LLMInsightResponse(status="success", insight=insight))
    except Exception as exc:
        ctx.logger.error("LLM insight failed: %s", exc)
        await ctx.send(sender, LLMInsightResponse(status="error", error=str(exc)))


@agent.on_message(model=LLMGenerateRequest, replies=LLMGenerateResponse)
async def handle_generate_request(ctx: Context, sender: str, msg: LLMGenerateRequest):
    try:
        candidates = service.generate_novel_candidates(msg.base_molecule)
        status = "success" if candidates or not service.last_error else "error"
        await ctx.send(
            sender,
            LLMGenerateResponse(
                status=status,
                error=service.last_error,
                candidates=candidates,
                is_available=service.is_available,
            ),
        )
    except Exception as exc:
        ctx.logger.error("LLM generation failed: %s", exc)
        await ctx.send(
            sender,
            LLMGenerateResponse(status="error", error=str(exc), is_available=service.is_available),
        )


if __name__ == "__main__":
    agent.run()
