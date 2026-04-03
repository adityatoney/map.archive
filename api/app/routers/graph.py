"""Knowledge graph context router — returns nodes and edges for visualization."""

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "disease", "pathway", "intervention", "lifestyle"


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphContextResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@router.get("/context", response_model=GraphContextResponse)
async def get_graph_context(
    icd_codes: list[str] = Query(..., description="ICD-10 codes to query"),
    condition_names: list[str] = Query(
        default=[], description="Matching condition names (same order as icd_codes)"
    ),
    depth: int = Query(1, ge=1, le=2, description="Traversal depth"),
    _user=Depends(get_current_user),
):
    """Return knowledge graph nodes and edges for the given ICD-10 codes.

    Caps output at 50 nodes to keep the visualization manageable.
    ``condition_names`` provides human-readable fallback labels for disease nodes
    when Neo4j doesn't have the disease name.
    """
    nodes: dict[str, GraphNode] = {}  # id -> node
    edges: list[GraphEdge] = []
    seen_edges: set[tuple[str, str, str]] = set()

    # Build ICD -> condition name fallback map
    fallback_names: dict[str, str] = {}
    for i, icd in enumerate(icd_codes[:20]):
        if i < len(condition_names) and condition_names[i]:
            fallback_names[icd] = condition_names[i]

    try:
        from app.services.graph_client import GraphClient

        graph_client = GraphClient()

        # Resolve ICD codes to disease names from Neo4j
        icd_to_name = await graph_client.get_disease_names(icd_codes[:20])

        for icd in icd_codes[:20]:  # Limit input codes
            # Get condition context (all relationships)
            context = await graph_client.get_condition_context(icd)

            # Add disease node: prefer Neo4j name > scan condition name > ICD code
            disease_id = f"disease:{icd}"
            if disease_id not in nodes:
                disease_name = icd_to_name.get(icd) or fallback_names.get(icd) or icd
                nodes[disease_id] = GraphNode(
                    id=disease_id, label=disease_name, type="disease"
                )

            for rec in context:
                target_type = rec.get("target_type", "").lower()
                target_name = rec.get("target_name", "Unknown")
                relationship = rec.get("relationship", "RELATED_TO")

                # Determine node type
                if target_type in ("pathway",):
                    node_type = "pathway"
                elif target_type in ("nutritionalfactor",):
                    node_type = "intervention"
                elif target_type in ("lifestyleintervention",):
                    node_type = "lifestyle"
                else:
                    node_type = "pathway"

                target_id = f"{node_type}:{target_name}"

                if target_id not in nodes:
                    nodes[target_id] = GraphNode(
                        id=target_id, label=target_name, type=node_type
                    )

                edge_key = (disease_id, target_id, relationship)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        GraphEdge(
                            source=disease_id,
                            target=target_id,
                            relationship=relationship,
                        )
                    )

                # Cap at 50 nodes
                if len(nodes) >= 50:
                    break
            if len(nodes) >= 50:
                break

        graph_client.close()

    except Exception as e:
        logger.warning("Knowledge graph context query failed: %s", e)

    return GraphContextResponse(
        nodes=list(nodes.values()),
        edges=edges,
    )
