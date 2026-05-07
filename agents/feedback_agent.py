"""Standalone uAgent wrapper for ``FeedbackService``."""

from __future__ import annotations

import sys
from pathlib import Path

from uagents import Agent, Context

sys.path.append(str(Path(__file__).parent.parent))

from models.messages import (
    FeedbackGetLogsRequest,
    FeedbackGetLogsResponse,
    FeedbackLogRequest,
    FeedbackLogResponse,
)
from services.feedback_service import FeedbackService

agent = Agent(
    name="FeedbackAgent",
    seed="feedback_agent_secret",
    port=8008,
    endpoint=["http://localhost:8008/submit"],
)
service = FeedbackService()


@agent.on_message(model=FeedbackLogRequest, replies=FeedbackLogResponse)
async def handle_log_request(ctx: Context, sender: str, msg: FeedbackLogRequest):
    try:
        entry = service.log_experiment(msg.payload)
        await ctx.send(sender, FeedbackLogResponse(status="success", entry=entry))
    except Exception as exc:
        ctx.logger.error("Feedback logging failed: %s", exc)
        await ctx.send(sender, FeedbackLogResponse(status="error", error=str(exc)))


@agent.on_message(model=FeedbackGetLogsRequest, replies=FeedbackGetLogsResponse)
async def handle_get_logs_request(ctx: Context, sender: str, msg: FeedbackGetLogsRequest):
    try:
        await ctx.send(
            sender,
            FeedbackGetLogsResponse(status="success", logs=service.get_all_logs()),
        )
    except Exception as exc:
        ctx.logger.error("Feedback log retrieval failed: %s", exc)
        await ctx.send(sender, FeedbackGetLogsResponse(status="error", error=str(exc)))


if __name__ == "__main__":
    agent.run()
