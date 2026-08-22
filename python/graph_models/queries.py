"""
Neo4j query engine for idx-bei investment research platform.

Provides graph database queries for:
- Company relationship modeling
- Network analysis
- Ownership chain traversal
- Director/shareholder network discovery
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RelationshipType(str, Enum):
    """Types of relationships in the graph."""
    DIRECTOR_OF = "DIRECTOR_OF"
    COMMISSIONER_OF = "COMMISSIONER_OF"
    CORPORATE_SECRETARY_OF = "CORPORATE_SECRETARY_OF"
    AUDIT_COMMITTEE_MEMBER_OF = "AUDIT_COMMITTEE_MEMBER_OF"
    OWNS = "OWNS"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    HAS_TRADE_DAY = "HAS_TRADE_DAY"


@dataclass
class PersonNode:
    """Represents a person (director, commissioner, etc.) in the graph."""
    name: str
    roles: List[Dict[str, Any]] = field(default_factory=list)
    companies: set = field(default_factory=set)

    def add_role(self, role_data: Dict[str, Any]):
        """Add a role to this person."""
        self.roles.append(role_data)
        if 'company' in role_data:
            self.companies.add(role_data['company'])

    def __hash__(self):
        return hash(self.name.lower())

    def __eq__(self, other):
        if not isinstance(other, PersonNode):
            return False
        return self.name.lower() == other.name.lower()


@dataclass
class CompanyNode:
    """Represents a company node in the graph."""
    ticker: str
    name: str = ""
    directors: List[PersonNode] = field(default_factory=list)
    commissioners: List[PersonNode] = field(default_factory=list)
    shareholders: List[Dict[str, Any]] = field(default_factory=list)
    subsidiaries: List[Dict[str, Any]] = field(default_factory=list)
    secretaries: List[Dict[str, Any]] = field(default_factory=list)
    audit_committee: List[Dict[str, Any]] = field(default_factory=list)

    def get_all_insiders(self) -> List[PersonNode]:
        """Get all insider nodes (directors + commissioners)."""
        return self.directors + self.commissioners

    def __repr__(self):
        return f"CompanyNode(ticker={self.ticker}, name={self.name})"


@dataclass
class Relationship:
    """Represents a relationship between two nodes."""
    start_node: Any
    end_node: Any
    rel_type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"Relationship({self.rel_type.value}, {self.start_node} -> {self.end_node})"


@dataclass
class NetworkResult:
    """Result of a network query."""
    ticker: str
    related_companies: List[Dict[str, Any]] = field(default_factory=list)
    connections: int = 0

    def __repr__(self):
        return f"NetworkResult(ticker={self.ticker}, {len(self.related_companies)} connections)"


class Neo4jQueryEngine:
    """Query engine for Neo4j database operations."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self):
        self._get_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def get_company(self, ticker: str) -> Optional[CompanyNode]:
        """Get company details from Neo4j."""
        driver = self._get_driver()
        with driver.session() as session:
            # Get company
            company_result = session.run(
                "MATCH (c:Company {kode: $ticker}) RETURN c",
                ticker=ticker
            )
            record = company_result.single()
            if not record:
                return None

            company_data = record['c']
            company = CompanyNode(
                ticker=ticker,
                name=company_data.get('companyName', ticker)
            )

            # Get directors
            directors_result = session.run(
                "MATCH (p:Insider)-[r:DIRECTOR_OF]->(c:Company {kode: $ticker}) "
                "RETURN p, r",
                ticker=ticker
            )
            for record in directors_result:
                person_data = record['p']
                person = PersonNode(name=person_data.get('name', ''))
                person.add_role({
                    'company': ticker,
                    'role': record['r'].get('jabatan', 'Director')
                })
                company.directors.append(person)

            # Get commissioners
            commissioners_result = session.run(
                "MATCH (p:Insider)-[r:COMMISSIONER_OF]->(c:Company {kode: $ticker}) "
                "RETURN p, r",
                ticker=ticker
            )
            for record in commissioners_result:
                person_data = record['p']
                person = PersonNode(name=person_data.get('name', ''))
                person.add_role({
                    'company': ticker,
                    'role': record['r'].get('jabatan', 'Commissioner')
                })
                company.commissioners.append(person)

            # Get shareholders
            shareholders_result = session.run(
                "MATCH (s:Insider)-[r:OWNS]->(c:Company {kode: $ticker}) "
                "RETURN s, r",
                ticker=ticker
            )
            for record in shareholders_result:
                company.shareholders.append({
                    'name': record['s'].get('name', ''),
                    'persentase': record['r'].get('persentase'),
                    'kategori': record['r'].get('kategori'),
                    'pengendali': record['r'].get('pengendali')
                })

            # Get subsidiaries
            subsidiaries_result = session.run(
                "MATCH (s:Subsidiary)-[r:SUBSIDIARY_OF]->(c:Company {kode: $ticker}) "
                "RETURN s, r",
                ticker=ticker
            )
            for record in subsidiaries_result:
                company.subsidiaries.append({
                    'name': record['s'].get('name', ''),
                    'persentase': record['r'].get('persentase'),
                    'bidang_usaha': record['s'].get('bidangUsaha')
                })

            return company

    def find_companies_through_directors(self, ticker: str, max_degree: int = 2) -> List[Dict[str, Any]]:
        """Find companies connected through shared directors."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                f"MATCH (c:Company {{kode: $ticker}})<-[:DIRECTOR_OF]-(d:Insider)-[:DIRECTOR_OF]->(other:Company) "
                f"WHERE other.kode <> $ticker "
                f"RETURN DISTINCT other.kode AS ticker, other.companyName AS name, collect(d.name) AS shared_directors "
                f"LIMIT $limit",
                ticker=ticker,
                limit=max_degree * 10
            )
            return [
                {'ticker': r['ticker'], 'name': r['name'], 'shared_directors': r['shared_directors'], 'degree': max_degree}
                for r in result
            ]

    def find_ownership_chain(self, ticker: str, depth: int = 3) -> List[Dict[str, Any]]:
        """Find ownership chain for a company."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                f"MATCH path = (c:Company {{kode: $ticker}})-[:SUBSIDIARY_OF*1..{depth}]->(s:Subsidiary) "
                f"RETURN s.name AS subsidiary_name, last(rel(path)).persentase AS ownership_pct",
                ticker=ticker
            )
            return [
                {'type': 'subsidiary', 'name': r['subsidiary_name'], 'ownership_percentage': r['ownership_pct']}
                for r in result
            ]

    def find_common_directors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Find directors with multiple board seats."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (d:Insider)-[:DIRECTOR_OF]->(c:Company) "
                "RETURN d.name AS name, collect(c.kode) AS companies, count(c) AS board_seats "
                "ORDER BY board_seats DESC "
                f"LIMIT {limit}"
            )
            return [
                {'name': r['name'], 'companies': r['companies'], 'board_seats': r['board_seats']}
                for r in result
            ]

    def find_largest_shareholders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Find largest shareholders across companies."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                f"MATCH (s:Insider)-[r:OWNS]->(c:Company) "
                f"RETURN s.name AS shareholder_name, c.kode AS company_ticker, "
                f"r.persentase AS percentage, r.kategori AS category "
                f"ORDER BY r.persentase DESC "
                f"LIMIT {limit}"
            )
            return [
                {'shareholder_name': r['shareholder_name'], 'company_ticker': r['company_ticker'],
                 'percentage': r['percentage'], 'category': r['category']}
                for r in result
            ]

    def find_controlled_companies(self) -> List[Dict[str, Any]]:
        """Find companies with controlling shareholders."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (s:Insider)-[r:OWNS]->(c:Company) "
                "WHERE r.pengendali = true "
                "RETURN c.kode AS ticker, c.companyName AS name, "
                "s.name AS controller, r.persentase AS percentage"
            )
            return [
                {'ticker': r['ticker'], 'name': r['name'],
                 'controller': r['controller'], 'percentage': r['percentage']}
                for r in result
            ]

    def get_industry_network(self, industry: str, max_depth: int = 2) -> NetworkResult:
        """Get network of companies in the same industry."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                f"MATCH (c:Company {{industry: $industry}}) "
                f"OPTIONAL MATCH (c)-[:DIRECTOR_OF|COMMISSIONER_OF]-(:Insider)-[:DIRECTOR_OF|COMMISSIONER_OF]->(related:Company) "
                f"WHERE related.industry = $industry AND related.kode <> c.kode "
                f"RETURN DISTINCT related.kode AS ticker, related.companyName AS name "
                f"LIMIT $limit",
                industry=industry,
                limit=max_depth * 20
            )
            companies = [{'ticker': r['ticker'], 'name': r['name']} for r in result]
            return NetworkResult(ticker=industry, related_companies=companies, connections=len(companies))


def get_company_network(ticker: str) -> Dict[str, Any]:
    """Convenience function to get company network."""
    import os

    from dotenv import load_dotenv
    load_dotenv()

    uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    with Neo4jQueryEngine(uri, user, password) as engine:
        company = engine.get_company(ticker)
        if company:
            directors = [p.name for p in company.directors]
            commissioners = [p.name for p in company.commissioners]
            return {
                'ticker': company.ticker,
                'name': company.name,
                'directors': directors,
                'commissioners': commissioners,
                'num_shareholders': len(company.shareholders),
                'num_subsidiaries': len(company.subsidiaries)
            }
        return {'ticker': ticker, 'error': 'Company not found'}


def find_director_connections(ticker: str, max_degree: int = 2) -> List[Dict[str, Any]]:
    """Find companies connected through directors."""
    import os

    from dotenv import load_dotenv
    load_dotenv()

    uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    with Neo4jQueryEngine(uri, user, password) as engine:
        return engine.find_companies_through_directors(ticker, max_degree)
