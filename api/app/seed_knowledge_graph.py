"""Seed Neo4j knowledge graph with curated biomedical data.

Populates Disease, Pathway, NutritionalFactor, LifestyleIntervention,
AnatomicalStructure, Gene, and Phenotype nodes with relationships
matching the queries in graph_client.py.

Usage:
    python -m app.seed_knowledge_graph

Idempotent: uses MERGE to avoid duplicates. Safe to run multiple times.
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def seed_knowledge_graph():
    """Seed Neo4j with curated biomedical knowledge."""
    from neo4j import GraphDatabase

    from app.config import get_settings
    from app.data.biomedical_knowledge import (
        DISEASES,
        LIFESTYLE_INTERVENTIONS,
        NUTRITIONAL_FACTORS,
        PATHWAYS,
    )

    settings = get_settings()

    if not settings.NEO4J_ENABLED:
        logger.warning("NEO4J_ENABLED is false — skipping knowledge graph seed.")
        return

    logger.info("Connecting to Neo4j at %s ...", settings.NEO4J_URI)
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j.")
    except Exception as e:
        logger.error("Cannot connect to Neo4j: %s", e)
        sys.exit(1)

    with driver.session() as session:
        # Step 1: Create uniqueness constraints (idempotent, also serve as indexes)
        logger.info("Creating constraints...")
        _create_constraints(session)

        # Step 2: Seed Pathway nodes
        logger.info("Seeding %d Pathway nodes...", len(PATHWAYS))
        for name, meta in PATHWAYS.items():
            session.run(
                "MERGE (p:Pathway {name: $name}) "
                "SET p.kegg_id = $kegg_id, p.category = $category",
                name=name,
                kegg_id=meta["kegg_id"],
                category=meta["category"],
            )

        # Step 3: Seed NutritionalFactor nodes
        logger.info("Seeding %d NutritionalFactor nodes...", len(NUTRITIONAL_FACTORS))
        for name, meta in NUTRITIONAL_FACTORS.items():
            session.run(
                "MERGE (n:NutritionalFactor {name: $name}) "
                "SET n.type = $type, n.evidence_level = $evidence_level",
                name=name,
                type=meta["type"],
                evidence_level=meta["evidence_level"],
            )

        # Step 4: Seed LifestyleIntervention nodes
        logger.info(
            "Seeding %d LifestyleIntervention nodes...", len(LIFESTYLE_INTERVENTIONS)
        )
        for name, meta in LIFESTYLE_INTERVENTIONS.items():
            session.run(
                "MERGE (li:LifestyleIntervention {name: $name}) "
                "SET li.category = $category, li.evidence_level = $evidence_level",
                name=name,
                category=meta["category"],
                evidence_level=meta["evidence_level"],
            )

        # Step 5: Seed Disease nodes + all outbound relationships
        logger.info("Seeding %d Disease nodes with relationships...", len(DISEASES))
        for icd10, disease in DISEASES.items():
            # Create Disease node
            session.run(
                "MERGE (d:Disease {icd10: $icd10}) SET d.name = $name",
                icd10=icd10,
                name=disease["name"],
            )

            # PART_OF_PATHWAY
            for pathway_name in disease["pathways"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (p:Pathway {name: $pathway}) "
                    "MERGE (d)-[:PART_OF_PATHWAY]->(p)",
                    icd10=icd10,
                    pathway=pathway_name,
                )

            # SUPPORTED_BY (nutritional factors)
            for nf_name in disease["nutritional_factors"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (n:NutritionalFactor {name: $nf}) "
                    "MERGE (d)-[:SUPPORTED_BY]->(n)",
                    icd10=icd10,
                    nf=nf_name,
                )

            # RESPONDS_TO (lifestyle interventions)
            for li_name in disease["lifestyle_interventions"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (li:LifestyleIntervention {name: $li}) "
                    "MERGE (d)-[:RESPONDS_TO]->(li)",
                    icd10=icd10,
                    li=li_name,
                )

            # AFFECTS (anatomical structures)
            for anat in disease["anatomical_structures"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (a:AnatomicalStructure {name: $anat}) "
                    "MERGE (d)-[:AFFECTS]->(a)",
                    icd10=icd10,
                    anat=anat,
                )

            # ASSOCIATED_GENE
            for gene in disease["genes"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (g:Gene {name: $gene}) "
                    "MERGE (d)-[:ASSOCIATED_GENE]->(g)",
                    icd10=icd10,
                    gene=gene,
                )

            # HAS_PHENOTYPE
            for pheno in disease["phenotypes"]:
                session.run(
                    "MATCH (d:Disease {icd10: $icd10}) "
                    "MERGE (ph:Phenotype {name: $pheno}) "
                    "MERGE (d)-[:HAS_PHENOTYPE]->(ph)",
                    icd10=icd10,
                    pheno=pheno,
                )

        # Step 6: COMORBID_WITH relationships
        logger.info("Seeding COMORBID_WITH relationships...")
        comorbid_count = 0
        for icd10, disease in DISEASES.items():
            for other_icd10 in disease.get("comorbid_with", []):
                if other_icd10 in DISEASES:
                    session.run(
                        "MATCH (d1:Disease {icd10: $icd1}), (d2:Disease {icd10: $icd2}) "
                        "MERGE (d1)-[:COMORBID_WITH]->(d2)",
                        icd1=icd10,
                        icd2=other_icd10,
                    )
                    comorbid_count += 1
        logger.info("  Created %d COMORBID_WITH relationships.", comorbid_count)

        # Step 7: Report stats
        logger.info("--- Knowledge Graph Stats ---")
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt "
            "ORDER BY cnt DESC"
        )
        for record in result:
            logger.info("  %s: %d nodes", record["label"], record["cnt"])

        result = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cnt "
            "ORDER BY cnt DESC"
        )
        total_rels = 0
        for record in result:
            logger.info("  %s: %d relationships", record["rel"], record["cnt"])
            total_rels += record["cnt"]

        logger.info("  TOTAL: %d relationships", total_rels)
        logger.info("Knowledge graph seeding complete!")

    driver.close()


def _create_constraints(session):
    """Create uniqueness constraints (idempotent)."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.icd10 IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pathway) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:NutritionalFactor) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (li:LifestyleIntervention) REQUIRE li.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AnatomicalStructure) REQUIRE a.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gene) REQUIRE g.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (ph:Phenotype) REQUIRE ph.name IS UNIQUE",
    ]
    for c in constraints:
        session.run(c)


if __name__ == "__main__":
    seed_knowledge_graph()
