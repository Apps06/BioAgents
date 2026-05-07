"""
BioAgents Exception Hierarchy
==============================
All service-layer errors are subclasses of ``BioAgentError``.

This module lives at the project root (not inside ``services/``) so that
both ``knowledge/`` and ``services/`` can import it without creating a
circular dependency.

The Flask error handler in ``server.py`` catches ``BioAgentError`` and returns
a structured JSON response using ``exc.http_status``. This contract means:

  - Business logic raises a *specific*, *descriptive* exception.
  - HTTP semantics (status codes, response shape) are decided exactly once,
    in the presentation layer (Flask).
  - Services are testable without an HTTP context.

Exception class → HTTP status mapping
--------------------------------------
MoleculeNotFoundError   404  — requested compound not in KB
InvalidInputError       400  — caller supplied bad/missing parameters
ExternalAPIError        502  — upstream dependency (PubChem) failed
KnowledgeBaseError      500  — KB failed to load or is internally inconsistent
"""

from __future__ import annotations


class BioAgentError(Exception):
    """Base class for all BioAgents service exceptions."""

    http_status: int = 422       # Unprocessable Entity — safe default

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r})"


class MoleculeNotFoundError(BioAgentError):
    """The requested molecule is not present in the knowledge base."""
    http_status = 404


class InvalidInputError(BioAgentError):
    """The caller supplied invalid or insufficient parameters."""
    http_status = 400


class ExternalAPIError(BioAgentError):
    """A required external service (e.g. PubChem) returned an error."""
    http_status = 502


class ExternalNotFoundError(BioAgentError):
    """An external lookup completed successfully but found no matching record."""
    http_status = 404


class KnowledgeBaseError(BioAgentError):
    """The knowledge base could not be loaded or is corrupt."""
    http_status = 500
