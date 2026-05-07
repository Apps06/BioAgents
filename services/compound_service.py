"""Compound lookup service backed by the MeTTa knowledge base."""

from __future__ import annotations

from knowledge.metta_handler import get_kb
from models.molecule import CompoundProfile, KnowledgeGraph
from services.base_service import BioAgentService, ServiceIdentity


class CompoundService(BioAgentService):
    identity = ServiceIdentity("CompoundAgent", "compound_agent_secret", 8002)

    def get_profile(self, molecule: str) -> CompoundProfile:
        return get_kb().get_compound_profile(molecule)

    def get_knowledge_graph(self) -> KnowledgeGraph:
        return get_kb().build_knowledge_graph()
