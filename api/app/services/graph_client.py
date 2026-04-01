"""Neo4j knowledge graph client with mock fallback.

Provides query methods for clinical reasoning: shared pathways,
condition context, interventions, and systemic patterns.
"""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class GraphClient:
    """Neo4j knowledge graph query interface."""

    def __init__(self):
        settings = get_settings()
        self.enabled = settings.NEO4J_ENABLED
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self._driver = None

    def _get_driver(self):
        """Lazy-load the Neo4j driver."""
        if self._driver is None and self.enabled:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", self.uri)
            except Exception as e:
                logger.warning("Neo4j unavailable: %s. Using mock mode.", e)
                self.enabled = False
                self._driver = None
        return self._driver

    async def find_shared_pathways(
        self, icd1: str, icd2: str
    ) -> list[dict[str, Any]]:
        """Find shared biological pathways between two conditions."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            query = """
            MATCH (d1:Disease {icd10: $icd1})-[:PART_OF_PATHWAY]->(p:Pathway)
                  <-[:PART_OF_PATHWAY]-(d2:Disease {icd10: $icd2})
            RETURN p.name AS pathway, p.kegg_id AS kegg_id,
                   d1.name AS disease1, d2.name AS disease2
            """
            with driver.session() as session:
                result = session.run(query, icd1=icd1, icd2=icd2)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("Neo4j query failed (shared_pathways): %s", e)
            return []

    async def get_condition_context(self, icd: str) -> list[dict[str, Any]]:
        """Get the full context for a condition (all relationships)."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            query = """
            MATCH (d:Disease {icd10: $icd})-[r]->(target)
            RETURN type(r) AS relationship,
                   labels(target)[0] AS target_type,
                   target.name AS target_name
            """
            with driver.session() as session:
                result = session.run(query, icd=icd)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("Neo4j query failed (condition_context): %s", e)
            return []

    async def find_interventions(
        self, icd_list: list[str]
    ) -> list[dict[str, Any]]:
        """Find nutritional/lifestyle interventions for a set of conditions."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            query = """
            MATCH (d:Disease)-[:SUPPORTED_BY]->(n:NutritionalFactor)
            WHERE d.icd10 IN $icd_list
            RETURN n.name AS intervention, n.type AS type,
                   count(d) AS conditions_supported,
                   collect(d.name) AS conditions
            ORDER BY conditions_supported DESC
            """
            with driver.session() as session:
                result = session.run(query, icd_list=icd_list)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("Neo4j query failed (interventions): %s", e)
            return []

    async def find_systemic_patterns(
        self, report_icds: list[str]
    ) -> list[dict[str, Any]]:
        """Find conditions sharing 2+ pathways (systemic patterns)."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            query = """
            MATCH (d1:Disease)-[:PART_OF_PATHWAY]->(p:Pathway)
                  <-[:PART_OF_PATHWAY]-(d2:Disease)
            WHERE d1.icd10 IN $report_icds
              AND d2.icd10 IN $report_icds
              AND d1 <> d2
            WITH d1, d2, count(p) AS shared_pathways,
                 collect(p.name) AS pathway_names
            WHERE shared_pathways >= 2
            RETURN d1.name AS disease1, d2.name AS disease2,
                   shared_pathways, pathway_names
            ORDER BY shared_pathways DESC
            """
            with driver.session() as session:
                result = session.run(query, report_icds=report_icds)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("Neo4j query failed (systemic_patterns): %s", e)
            return []

    async def find_lifestyle_interventions(
        self, icd_list: list[str]
    ) -> list[dict[str, Any]]:
        """Find lifestyle interventions ranked by evidence and coverage."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            query = """
            MATCH (d:Disease)-[:RESPONDS_TO]->(li:LifestyleIntervention)
            WHERE d.icd10 IN $icd_list
            RETURN li.name AS intervention, li.category AS category,
                   li.evidence_level AS evidence_level,
                   count(d) AS conditions_addressed,
                   collect(d.name) AS targets
            ORDER BY conditions_addressed DESC, li.evidence_level DESC
            """
            with driver.session() as session:
                result = session.run(query, icd_list=icd_list)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning("Neo4j query failed (lifestyle_interventions): %s", e)
            return []

    def close(self):
        """Close the Neo4j driver."""
        if self._driver:
            self._driver.close()
            self._driver = None
