"""
BioAgents MeTTa Knowledge Base
================================
Parses a MeTTa S-expression fact file into a queryable, indexed in-memory
knowledge base that returns typed domain objects.

Why not the ``hyperon`` package?
---------------------------------
The official ``hyperon`` library ships C-extension wheels that are not
available for Python 3.13 on Windows.  We implement a purpose-built parser
for the flat, single-level S-expression subset that our KB uses.

Indexing strategy
-----------------
All facts are indexed into specialised dictionaries on load so that every
query is O(1) or O(k) in the result set size, never O(n) across all facts.

Data flow
---------
  molecules.metta
    → _parse()           raw token lists
    → _index()           type-aware dicts (properties, similar, interactions)
    → public methods     typed domain objects (MoleculeProperties, etc.)
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from models.molecule import (
    CandidateCompound,
    DrugInteraction,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    MoleculeProperties,
    CompoundProfile,
)
from exceptions import InvalidInputError, KnowledgeBaseError, MoleculeNotFoundError

logger = logging.getLogger(__name__)
_VALID_SEVERITIES = {"low", "moderate", "high"}

_FACT_RE = re.compile(r"^\(([^()]+)\)\s*$")   # flat (a b c …) only, no nesting


# ---------------------------------------------------------------------------
# Internal parser
# ---------------------------------------------------------------------------

def _parse(path: Path) -> list[list[str]]:
    """
    Scan a MeTTa file and return a list of token-lists.

    Rules:
      - Text after ``;`` on any line is a comment and is discarded.
      - Lines containing ``:-`` (MeTTa inference rules) are skipped.
      - Nested S-expressions (lines with multiple ``()``) are skipped with
        a warning — our KB deliberately avoids them.
      - Every token is returned as-is (strings, numbers remain as str).
    """
    facts: list[list[str]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.split(";")[0].strip()
            if not line or ":-" in line:
                continue
            m = _FACT_RE.match(line)
            if not m:
                if line.startswith("("):
                    logger.debug("Skipping complex expression at line %d: %s", lineno, line)
                continue
            tokens = m.group(1).split()
            if len(tokens) < 2:
                logger.warning("Degenerate fact (< 2 tokens) at line %d: %s", lineno, line)
                continue
            facts.append(tokens)
    return facts


def _to_float(value: str, context: str) -> Optional[float]:
    """Convert a token to float, logging a warning on failure."""
    try:
        return float(value)
    except ValueError:
        logger.warning("Expected numeric value in %s, got %r", context, value)
        return None


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

class MeTTaKnowledgeBase:
    """
    Queryable, indexed in-memory knowledge base.

    All public methods return typed domain objects.  No raw dicts or
    bare strings leak out of this class.
    """

    def __init__(self, kb_path: Optional[Path] = None) -> None:
        if kb_path is None:
            kb_path = Path(__file__).parent / "molecules.metta"

        if not kb_path.exists():
            raise KnowledgeBaseError(f"Knowledge base file not found: {kb_path}")

        facts = _parse(kb_path)
        if not facts:
            raise KnowledgeBaseError(f"Knowledge base parsed zero facts from: {kb_path}")

        (
            self._molecules,     # str  → MoleculeProperties
            self._similar,       # str  → set[str]   (undirected)
            self._interactions,  # str  → list[DrugInteraction]
        ) = _index(facts)

        logger.info(
            "KB loaded: %d molecules, %d similarity pairs, %d interactions",
            len(self._molecules),
            sum(len(v) for v in self._similar.values()) // 2,
            sum(len(v) for v in self._interactions.values()),
        )
        self._canonical = {k.lower(): k for k in self._molecules.keys()}

    # ------------------------------------------------------------------
    # Molecule queries
    # ------------------------------------------------------------------

    def all_molecules(self) -> list[str]:
        """Return a sorted list of all molecule names in the KB."""
        return sorted(self._molecules.keys())

    def has_molecule(self, name: str) -> bool:
        return bool(name) and name.strip().lower() in self._canonical

    def resolve_name(self, name: str) -> str:
        """Return the canonical KB spelling for *name* or raise a domain error."""
        if not name or not name.strip():
            raise InvalidInputError("Molecule name must be a non-empty string.")

        canonical = self._canonical.get(name.strip().lower())
        if not canonical:
            known = ", ".join(sorted(self._molecules)[:10])
            raise MoleculeNotFoundError(
                f"'{name}' is not in the knowledge base.  "
                f"Known molecules include: {known}…"
            )
        return canonical

    def _resolve(self, name: str) -> str:
        """Backward-compatible alias; new code should use ``resolve_name``."""
        return self.resolve_name(name)

    def get_properties(self, name: str) -> MoleculeProperties:
        """
        Return typed properties for *name*.

        Raises ``MoleculeNotFoundError`` if *name* is unknown.
        """
        resolved = self._resolve(name)
        return self._molecules[resolved]

    def get_similar(self, name: str) -> list[str]:
        """Return molecules structurally similar to *name* (sorted)."""
        resolved = self._resolve(name)
        return sorted(self._similar.get(resolved, set()))

    def get_interactions(self, name: str) -> list[DrugInteraction]:
        """Return all known drug interactions for *name*."""
        resolved = self._resolve(name)
        return list(self._interactions.get(resolved, []))

    def get_compound_profile(self, name: str) -> CompoundProfile:
        """Return the complete profile for *name* (properties + relations)."""
        resolved = self._resolve(name)
        return CompoundProfile(
            molecule=resolved,
            properties=self.get_properties(resolved),
            similar_compounds=self.get_similar(resolved),
            known_interactions=self.get_interactions(resolved),
        )

    def get_all_candidates(self) -> list[CandidateCompound]:
        """Return every molecule as a CandidateCompound (for full scans)."""
        return [
            CandidateCompound(molecule=n, properties=p)
            for n, p in self._molecules.items()
        ]

    # ------------------------------------------------------------------
    # Graph builder
    # ------------------------------------------------------------------

    def build_knowledge_graph(self) -> KnowledgeGraph:
        """
        Build a typed graph payload for react-force-graph-2d.

        Nodes are colour-grouped by primary drug category.
        Edges come in two types:
          ``similar``      — structural similarity (undirected, deduplicated)
          ``interaction``  — known DDI (directed, coloured by severity)
        """
        category_group: dict[str, int] = {}
        nodes: list[KnowledgeGraphNode] = []

        for name, props in self._molecules.items():
            primary_cat = props.categories[0] if props.categories else "Unknown"
            if primary_cat not in category_group:
                category_group[primary_cat] = len(category_group) + 1

            nodes.append(KnowledgeGraphNode(
                id=name,
                group=category_group[primary_cat],
                category=primary_cat,
                val=round((props.activity_score or 0.5) * 10, 2),
            ))

        seen_similar: set[frozenset[str]] = set()
        seen_interactions: set[frozenset[str]] = set()
        edges: list[KnowledgeGraphEdge] = []

        for name in self._molecules:
            for other in self._similar.get(name, set()):
                key = frozenset({name, other})
                if key not in seen_similar:
                    seen_similar.add(key)
                    edges.append(KnowledgeGraphEdge(
                        source=name, target=other, value=1, type="similar",
                    ))

            for ix in self._interactions.get(name, []):
                if ix.drug in self._molecules:
                    key = frozenset({name, ix.drug})
                    if key in seen_interactions:
                        continue
                    seen_interactions.add(key)
                    edges.append(KnowledgeGraphEdge(
                        source=name, target=ix.drug, value=2,
                        type="interaction", severity=ix.severity,
                    ))

        return KnowledgeGraph(nodes=nodes, links=edges)


# ---------------------------------------------------------------------------
# Indexer (separated for testability)
# ---------------------------------------------------------------------------

def _index(
    facts: list[list[str]],
) -> tuple[
    dict[str, MoleculeProperties],
    dict[str, set[str]],
    dict[str, list[DrugInteraction]],
]:
    """
    Build all KB indices from the raw parsed facts in a single pass.

    Returns:
        molecules    — name → MoleculeProperties
        similar      — name → set of similar molecule names
        interactions — name → list of DrugInteraction
    """
    # Collect raw token lists per predicate
    raw: dict[str, list[list[str]]] = defaultdict(list)
    molecule_names: set[str] = set()

    for fact in facts:
        predicate = fact[0]
        if predicate == "molecule":
            molecule_names.add(fact[1])
        raw[predicate].append(fact)

    def _scalar(predicate: str, subject: str) -> Optional[str]:
        for f in raw[predicate]:
            if f[1] == subject and len(f) >= 3:
                return f[2]
        return None

    def _multi(predicate: str, subject: str) -> list[str]:
        values: list[str] = []
        for f in raw[predicate]:
            if f[1] == subject and len(f) >= 3:
                values.extend(f[2:])
        return values

    # Build molecule properties index
    molecules: dict[str, MoleculeProperties] = {}
    for name in sorted(molecule_names):
        mw_raw  = _scalar("molecular_weight", name)
        act_raw = _scalar("activity_score", name)
        sel_raw = _scalar("selectivity", name)
        stab_raw = _scalar("stability", name)

        molecules[name] = MoleculeProperties(
            molecular_weight  = _to_float(mw_raw,  f"{name}.molecular_weight")  if mw_raw  else None,
            formula           = _scalar("formula", name),
            categories        = _multi("category", name),
            targets           = _multi("target", name),
            functional_groups = _multi("functional_group", name),
            activity_score    = _to_float(act_raw, f"{name}.activity_score") if act_raw else None,
            selectivity       = _to_float(sel_raw, f"{name}.selectivity") if sel_raw else None,
            stability_h       = _to_float(stab_raw,  f"{name}.stability")      if stab_raw  else None,
        )

        for label, value in (
            ("activity_score", molecules[name].activity_score),
            ("selectivity", molecules[name].selectivity),
        ):
            if value is not None and not (0.0 <= value <= 1.0):
                raise KnowledgeBaseError(
                    f"{name}.{label} must be in [0.0, 1.0], got {value}."
                )

    # Build similarity index (undirected — store both directions)
    similar: dict[str, set[str]] = defaultdict(set)
    for f in raw["similar_to"]:
        if len(f) >= 3:
            a, b = f[1], f[2]
            _require_known(molecule_names, a, "similar_to")
            _require_known(molecule_names, b, "similar_to")
            similar[a].add(b)
            similar[b].add(a)

    # Build interaction index (bidirectional store)
    interactions: dict[str, list[DrugInteraction]] = defaultdict(list)
    for f in raw["interacts"]:
        if len(f) >= 5:
            mol_a, mol_b, effect, severity = f[1], f[2], f[3], f[4]
            _require_known(molecule_names, mol_a, "interacts")
            _require_known(molecule_names, mol_b, "interacts")
            if severity.lower() not in _VALID_SEVERITIES:
                raise KnowledgeBaseError(
                    f"Interaction {mol_a}/{mol_b} has invalid severity '{severity}'. "
                    f"Expected one of: {', '.join(sorted(_VALID_SEVERITIES))}."
                )
            interactions[mol_a].append(DrugInteraction(drug=mol_b, effect=effect, severity=severity))
            interactions[mol_b].append(DrugInteraction(drug=mol_a, effect=effect, severity=severity))

    return dict(molecules), dict(similar), dict(interactions)


def _require_known(molecule_names: set[str], name: str, predicate: str) -> None:
    if name not in molecule_names:
        raise KnowledgeBaseError(
            f"Fact '{predicate}' references unknown molecule '{name}'. "
            "Declare it with a (molecule ...) fact first."
        )


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once on first import, shared across services
# ---------------------------------------------------------------------------

_KB: Optional[MeTTaKnowledgeBase] = None


def get_kb() -> MeTTaKnowledgeBase:
    """Return the module-level KB singleton, initialising on first call."""
    global _KB
    if _KB is None:
        _KB = MeTTaKnowledgeBase()
    return _KB
