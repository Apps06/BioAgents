"""Reaction and interaction assessment service."""

from __future__ import annotations

from knowledge.metta_handler import get_kb
from models.molecule import DrugInteraction, InteractionReport
from services.base_service import BioAgentService, ServiceIdentity


class ReactionService(BioAgentService):
    identity = ServiceIdentity("ReactionAgent", "reaction_agent_secret", 8004)

    def simulate_reaction(self, mol1: str, mol2: str) -> InteractionReport:
        kb = get_kb()
        left = kb.resolve_name(mol1)
        right = kb.resolve_name(mol2)
        props_left = kb.get_properties(left)
        props_right = kb.get_properties(right)

        explicit = [
            interaction
            for interaction in kb.get_interactions(left)
            if interaction.drug == right
        ]
        shared_targets = sorted(set(props_left.targets).intersection(props_right.targets))
        risk_level = self._risk_level(explicit, shared_targets)
        warnings = self._warnings(left, right, explicit, shared_targets, risk_level)

        return InteractionReport(
            compound_1=left,
            compound_2=right,
            targets_1=props_left.targets,
            targets_2=props_right.targets,
            shared_targets=shared_targets,
            explicit_interactions=explicit,
            risk_level=risk_level,
            warnings=warnings,
        )

    @staticmethod
    def _risk_level(explicit: list[DrugInteraction], shared_targets: list[str]) -> str:
        highest = max((item.severity_rank for item in explicit), default=0)
        if highest >= 3:
            return "High"
        if highest == 2:
            return "Moderate"
        if highest == 1 or shared_targets:
            return "Low"
        return "Low"

    @staticmethod
    def _warnings(
        left: str,
        right: str,
        explicit: list[DrugInteraction],
        shared_targets: list[str],
        risk_level: str,
    ) -> list[str]:
        warnings = []
        for interaction in explicit:
            warnings.append(
                f"{left} has a known {interaction.severity} interaction with "
                f"{right}: {interaction.effect.replace('_', ' ')}."
            )
        if shared_targets:
            warnings.append(
                "Shared reaction targets may create competition or pathway coupling: "
                + ", ".join(shared_targets)
                + "."
            )
        if not warnings:
            warnings.append("No explicit interaction is recorded in the local knowledge base.")
        if risk_level == "High":
            warnings.append("Treat this pair as high-risk until experimentally validated.")
        return warnings
