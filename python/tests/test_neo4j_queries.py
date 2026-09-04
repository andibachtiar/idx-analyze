"""
Tests for Neo4j Relationship Intelligence (Phase 7).

Tests the graph database query capabilities including:
- Company node retrieval
- Director/shareholder relationships
- Ownership chains
- Related company discovery
- Network analytics
"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from graph_models.queries import (
    CompanyNode,
    Neo4jQueryEngine,
    NetworkResult,
    PersonNode,
    Relationship,
    RelationshipType,
)

# =============================================================================
# MOCK DATA FOR TESTING
# =============================================================================

MOCK_COMPANY_DATA = {
    'kode': 'BBCA',
    'companyName': 'Bank Central Asia Tbk',
    'sector': 'Finance',
    'industry': 'Banking'
}

MOCK_DIRECTOR_DATA = [
    {'name': 'Artaxias Sumarno', 'jabatan': 'President Director', 'afiliasi': False},
    {'name': 'Jahjan Santoso', 'jabatan': 'Director', 'afiliasi': True}
]

MOCK_COMMISSIONER_DATA = [
    {'name': 'Ferdinan Djaja', 'jabatan': 'Commissioner', 'independen': False},
    {'name': 'Kunio Warnoko', 'jabatan': 'Independent Commissioner', 'independen': True}
]

MOCK_SHAREHOLDER_DATA = [
    {'name': 'BlackRock Inc.', 'persentase': 5.5, 'kategori': 'Foreign', 'pengendali': False},
    {'name': 'Government of Indonesia', 'persentase': 15.0, 'kategori': 'State', 'pengendali': True}
]

MOCK_SUBSIDIARY_DATA = [
    {'name': 'BCA Securities', 'persentase': 100.0, 'bidang_usaha': 'Securities'},
    {'name': 'BCA Asset Management', 'persentase': 100.0, 'bidang_usaha': 'Asset Management'}
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_mock_session(results=None):
    """Create a mock Neo4j session for testing."""
    mock_session = MagicMock()
    mock_result = MagicMock()

    if results is None:
        results = []

    mock_result.single.return_value = results[0] if results else None
    mock_result.__iter__ = lambda self: iter(results)

    mock_session.run.return_value = mock_result
    return mock_session


def create_mock_driver():
    """Create a mock Neo4j driver for testing."""
    mock_driver = MagicMock()
    mock_session = create_mock_session()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return mock_driver


# =============================================================================
# TESTS FOR DATA MODELS
# =============================================================================

class TestPersonNode:
    """Tests for PersonNode dataclass."""

    def test_create_person(self):
        person = PersonNode(name="John Doe")
        assert person.name == "John Doe"
        assert len(person.roles) == 0
        assert len(person.companies) == 0

    def test_add_role(self):
        person = PersonNode(name="John Doe")
        person.add_role({'company': 'BBCA', 'role': 'director'})
        assert len(person.roles) == 1
        assert 'BBCA' in person.companies

    def test_equality(self):
        p1 = PersonNode(name="John Doe")
        p2 = PersonNode(name="john doe")
        assert p1 == p2

    def test_hash(self):
        p1 = PersonNode(name="John Doe")
        p2 = PersonNode(name="john doe")
        assert hash(p1) == hash(p2)


class TestCompanyNode:
    """Tests for CompanyNode dataclass."""

    def test_create_company (self):
        company = CompanyNode(ticker="BBCA", name="Bank Central Asia")
        assert company.ticker == "BBCA"
        assert company.name == "Bank Central Asia"
        assert len(company.directors) == 0
        assert len(company.commissioners) == 0

    def test_get_all_insiders(self):
        company = CompanyNode(ticker="BBCA")
        director = PersonNode(name="John Doe")
        commissioner = PersonNode(name="Jane Smith")
        company.directors.append(director)
        company.commissioners.append(commissioner)

        insiders = company.get_all_insiders()
        assert len(insiders) == 2

    def test_repr(self):
        company = CompanyNode(ticker="BBCA", name="Bank Central Asia")
        assert "BBCA" in repr(company)


class TestNetworkResult:
    """Tests for NetworkResult dataclass."""

    def test_create_result(self):
        result = NetworkResult(ticker="BBCA")
        assert result.ticker == "BBCA"
        assert len(result.related_companies) == 0

    def test_repr(self):
        result = NetworkResult(ticker="BBCA", related_companies=[{'ticker': 'ADRO'}])
        assert "BBCA" in repr(result)
        assert "1 connections" in repr(result)


# =============================================================================
# TESTS FOR QUERY ENGINE (Mocked)
# =============================================================================

class TestNeo4jQueryEngine:
    """Tests for Neo4jQueryEngine with mocked Neo4j."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = Neo4jQueryEngine(
            uri="neo4j://localhost:7687",
            user="neo4j",
            password="test_password"
        )

    def test_init(self):
        """Test engine initialization."""
        assert self.engine.uri == "neo4j://localhost:7687"
        assert self.engine.user == "neo4j"
        assert self.engine.password == "test_password"
        assert self.engine._driver is None

    @patch('neo4j.GraphDatabase')
    def test_get_driver(self, mock_graphdb):
        """Test driver creation."""
        mock_driver = MagicMock()
        mock_graphdb.driver.return_value = mock_driver

        driver = self.engine._get_driver()
        assert driver == mock_driver
        mock_graphdb.driver.assert_called_once()

    def test_close(self):
        """Test driver closure."""
        mock_driver = MagicMock()
        self.engine._driver = mock_driver
        self.engine.close()
        mock_driver.close.assert_called_once()
        assert self.engine._driver is None

    @patch('neo4j.GraphDatabase')
    def test_context_manager(self, mock_graphdb):
        """Test context manager usage."""
        mock_driver = MagicMock()
        mock_graphdb.driver.return_value = mock_driver

        with Neo4jQueryEngine("bolt://test", "user", "pass") as engine:
            assert engine._driver == mock_driver

        mock_driver.close.assert_called_once()


class TestCompanyQueries:
    """Tests for company-related queries."""

    @patch('neo4j.GraphDatabase')
    def test_get_company_not_found(self, mock_graphdb):
        """Test getting non-existent company."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        result = engine.get_company("NONEXIST")
        assert result is None

    @patch('neo4j.GraphDatabase')
    def test_get_company_with_data(self, mock_graphdb):
        """Test getting company with full data."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock company result
        mock_company_result = MagicMock()
        mock_company_result.single.return_value = {'c': MOCK_COMPANY_DATA}

        # Mock directors result - return record-like objects with ['p'] and ['r'] keys
        def _make_record(data, node_key='p', rel_key='r'):
            rec = MagicMock()
            def getitem(self, key):
                if key == node_key:
                    return data
                elif key == rel_key:
                    return {'jabatan': data.get('jabatan', 'Director'), 'persentase': data.get('persentase'), 'kategori': data.get('kategori'), 'pengendali': data.get('pengendali')}
                raise KeyError(key)
            rec.__getitem__ = getitem
            return rec

        mock_directors_result = MagicMock()
        mock_directors_result.__iter__ = lambda self: iter([_make_record(d) for d in MOCK_DIRECTOR_DATA])

        # Mock commissioners result
        mock_commissioners_result = MagicMock()
        mock_commissioners_result.__iter__ = lambda self: iter([_make_record(c) for c in MOCK_COMMISSIONER_DATA])

        # Mock shareholders result
        mock_shareholders_result = MagicMock()
        mock_shareholders_result.__iter__ = lambda self: iter([_make_record(s, node_key='s') for s in MOCK_SHAREHOLDER_DATA])

        # Mock subsidiaries result
        mock_subsidiaries_result = MagicMock()
        mock_subsidiaries_result.__iter__ = lambda self: iter([_make_record(s, node_key='s') for s in MOCK_SUBSIDIARY_DATA])

        def run_side_effect(query, **kwargs):
            if 'RETURN c' in query:
                return mock_company_result
            elif 'DIRECTOR_OF' in query:
                return mock_directors_result
            elif 'COMMISSIONER_OF' in query:
                return mock_commissioners_result
            elif 'OWNS' in query:
                return mock_shareholders_result
            elif 'SUBSIDIARY_OF' in query:
                return mock_subsidiaries_result
            return MagicMock()

        mock_session.run.side_effect = run_side_effect
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        result = engine.get_company("BBCA")

        assert result is not None
        assert result.ticker == "BBCA"
        assert result.name == "Bank Central Asia Tbk"
        assert len(result.directors) == 2
        assert len(result.commissioners) == 2
        assert len(result.shareholders) == 2
        assert len(result.subsidiaries) == 2


class TestRelationshipQueries:
    """Tests for relationship traversal queries."""

    @patch('neo4j.GraphDatabase')
    def test_find_companies_through_directors(self, mock_graphdb):
        """Test finding companies connected through directors."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result for director connections
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {'ticker': 'ADRO', 'name': 'Adaro Indonesia', 'shared_directors': ['John Doe']},
            {'ticker': 'TLKM', 'name': 'Telkom Indonesia', 'shared_directors': ['Jane Smith']}
        ])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        results = engine.find_companies_through_directors("BBCA", max_degree=1)

        assert len(results) == 2
        assert results[0]['ticker'] == 'ADRO'
        assert results[0]['degree'] == 1

    @patch('neo4j.GraphDatabase')
    def test_find_ownership_chain(self, mock_graphdb):
        """Test finding ownership chain."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result for ownership chain
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {'subsidiary_name': 'BCA Securities', 'ownership_pct': 100.0},
            {'subsidiary_name': 'BCA Asset Management', 'ownership_pct': 100.0}
        ])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        chain = engine.find_ownership_chain("BBCA")

        assert len(chain) == 2
        assert chain[0]['type'] == 'subsidiary'
        assert chain[0]['ownership_percentage'] == 100.0


class TestAnalyticsQueries:
    """Tests for analytics queries."""

    @patch('neo4j.GraphDatabase')
    def test_find_common_directors(self, mock_graphdb):
        """Test finding directors with multiple board seats."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {'name': 'John Doe', 'companies': ['BBCA', 'ADRO'], 'board_seats': 2},
            {'name': 'Jane Smith', 'companies': ['BBCA', 'TLKM', 'ASII'], 'board_seats': 3}
        ])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        results = engine.find_common_directors()

        assert len(results) == 2
        assert results[1]['board_seats'] == 3  # Jane has more seats

    @patch('neo4j.GraphDatabase')
    def test_find_largest_shareholders(self, mock_graphdb):
        """Test finding largest shareholders."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {'shareholder_name': 'Govt of Indonesia', 'company_ticker': 'BBCA',
             'percentage': 15.0, 'category': 'State'},
            {'shareholder_name': 'BlackRock', 'company_ticker': 'BBCA',
             'percentage': 5.5, 'category': 'Foreign'}
        ])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        results = engine.find_largest_shareholders(limit=10)

        assert len(results) == 2
        assert results[0]['percentage'] == 15.0

    @patch('neo4j.GraphDatabase')
    def test_find_controlled_companies(self, mock_graphdb):
        """Test finding companies with controlling shareholders."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            {'ticker': 'BBCA', 'name': 'Bank Central Asia',
             'controller': 'Govt of Indonesia', 'percentage': 15.0}
        ])
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        engine = Neo4jQueryEngine("bolt://test", "user", "pass")
        results = engine.find_controlled_companies()

        assert len(results) == 1
        assert results[0]['controller'] == 'Govt of Indonesia'


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('neo4j.GraphDatabase')
    def test_get_company_network(self, mock_graphdb):
        """Test get_company_network convenience function."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_graphdb.driver.return_value = mock_driver

        from graph_models.queries import get_company_network
        result = get_company_network("BBCA")

        assert 'ticker' in result
        assert result['ticker'] == 'BBCA'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
