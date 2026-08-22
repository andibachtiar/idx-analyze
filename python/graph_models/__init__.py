"""
Graph models package for idx-bei investment research platform.

Provides graph database integration for:
- Company relationship modeling
- Network analysis
- Ownership chain traversal
- Director/shareholder network discovery
"""

from .queries import (
    CompanyNode,
    Neo4jQueryEngine,
    NetworkResult,
    PersonNode,
    Relationship,
    RelationshipType,
    find_director_connections,
    get_company_network,
)

__all__ = [
    # Query Engine
    "Neo4jQueryEngine",

    # Models
    "RelationshipType",
    "PersonNode",
    "CompanyNode",
    "Relationship",
    "NetworkResult",

    # Convenience functions
    "get_company_network",
    "find_director_connections",
]
