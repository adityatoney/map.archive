"""Clustering service — groups condition embeddings using HDBSCAN + UMAP.

With real embeddings from BioClinical ModernBERT, produces meaningful condition
groupings. Falls back to trivial clusters when embeddings are mock/insufficient.
"""

import logging
from collections import Counter

import numpy as np

logger = logging.getLogger(__name__)


class ClustererService:
    """Cluster condition embeddings and produce 2D visualization coordinates."""

    def __init__(self, umap_n_components: int = 2):
        self.umap_n_components = umap_n_components

    def cluster_entries(
        self,
        embeddings: list[list[float]],
        condition_names: list[str],
        organ_systems: list[str] | None = None,
    ) -> dict:
        """Run HDBSCAN clustering on UMAP-reduced embeddings.

        Args:
            embeddings: List of 768-dim vectors
            condition_names: Corresponding condition names
            organ_systems: Optional organ system labels for richer summaries

        Returns:
            {
                "labels": list[int],  # cluster assignment per entry (-1 = noise)
                "umap_coords": list[list[float]],  # 2D coordinates for viz
                "cluster_summaries": dict[int, dict],  # per-cluster info
            }
        """
        if not embeddings or len(embeddings) < 2:
            return {
                "labels": [0] * len(embeddings),
                "umap_coords": [[0.0, 0.0]] * len(embeddings),
                "cluster_summaries": {
                    0: {
                        "name": "All Conditions",
                        "size": len(embeddings),
                        "representative": condition_names[0] if condition_names else "",
                        "conditions": condition_names[:],
                        "organ_systems": [],
                    }
                },
            }

        n = len(embeddings)
        params = self._compute_params(n)
        emb_array = np.array(embeddings)

        logger.info(
            "Clustering %d entries (min_cluster_size=%d, n_neighbors=%d)",
            n, params["min_cluster_size"], params["n_neighbors"],
        )

        # UMAP dimensionality reduction for 2D visualization
        umap_coords = self._reduce_umap(emb_array, params["n_neighbors"])

        # HDBSCAN clustering on intermediate UMAP reduction
        labels = self._cluster_hdbscan(emb_array, params)

        # Build cluster summaries
        cluster_summaries = self._summarize_clusters(
            labels, condition_names, emb_array, organ_systems
        )

        return {
            "labels": labels.tolist() if isinstance(labels, np.ndarray) else labels,
            "umap_coords": umap_coords.tolist()
            if isinstance(umap_coords, np.ndarray)
            else umap_coords,
            "cluster_summaries": cluster_summaries,
        }

    def _compute_params(self, n: int) -> dict:
        """Select clustering parameters based on dataset size."""
        if n < 30:
            return {
                "min_cluster_size": 2,
                "n_neighbors": min(5, n - 1),
                "umap_intermediate_dims": min(10, n - 1),
            }
        elif n < 100:
            return {
                "min_cluster_size": 3,
                "n_neighbors": min(10, n - 1),
                "umap_intermediate_dims": min(30, n - 1),
            }
        elif n < 300:
            return {
                "min_cluster_size": 5,
                "n_neighbors": 15,
                "umap_intermediate_dims": 50,
            }
        else:
            return {
                "min_cluster_size": 8,
                "n_neighbors": 15,
                "umap_intermediate_dims": 50,
            }

    def _reduce_umap(self, embeddings: np.ndarray, n_neighbors: int) -> np.ndarray:
        """Reduce embeddings to 2D using UMAP."""
        try:
            import umap

            reducer = umap.UMAP(
                n_components=self.umap_n_components,
                n_neighbors=min(n_neighbors, len(embeddings) - 1),
                min_dist=0.1,
                metric="cosine",
                random_state=42,
            )
            return reducer.fit_transform(embeddings)
        except Exception as e:
            logger.warning("UMAP reduction failed: %s. Using random 2D coords.", e)
            rng = np.random.RandomState(42)
            return rng.randn(len(embeddings), 2)

    def _cluster_hdbscan(self, embeddings: np.ndarray, params: dict) -> np.ndarray:
        """Cluster embeddings using scikit-learn's HDBSCAN (sklearn >= 1.3)."""
        try:
            from sklearn.cluster import HDBSCAN

            min_size = params["min_cluster_size"]
            intermediate_dims = params["umap_intermediate_dims"]
            n_neighbors = params["n_neighbors"]

            # Use UMAP intermediate reduction for clustering (better than raw 768D)
            try:
                import umap

                reducer = umap.UMAP(
                    n_components=min(intermediate_dims, len(embeddings) - 1),
                    n_neighbors=min(n_neighbors, len(embeddings) - 1),
                    metric="cosine",
                    random_state=42,
                )
                reduced = reducer.fit_transform(embeddings)
            except Exception:
                reduced = embeddings

            clusterer = HDBSCAN(
                min_cluster_size=min_size,
                metric="euclidean",
                cluster_selection_method="eom",
                cluster_selection_epsilon=0.05,
            )
            labels = clusterer.fit_predict(reduced)

            # Noise fallback: if >80% are noise, rerun with min_cluster_size=2
            noise_ratio = np.sum(labels == -1) / len(labels)
            if noise_ratio > 0.8 and min_size > 2:
                logger.info(
                    "%.0f%% noise with min_cluster_size=%d, retrying with 2",
                    noise_ratio * 100, min_size,
                )
                clusterer_retry = HDBSCAN(
                    min_cluster_size=2,
                    metric="euclidean",
                    cluster_selection_method="eom",
                    cluster_selection_epsilon=0.05,
                )
                labels = clusterer_retry.fit_predict(reduced)

            n_clusters = len(set(labels.tolist()) - {-1})
            n_noise = int(np.sum(labels == -1))
            logger.info(
                "HDBSCAN found %d clusters, %d noise points (%.0f%%)",
                n_clusters, n_noise, (n_noise / len(labels)) * 100,
            )
            return labels

        except Exception as e:
            logger.warning("HDBSCAN clustering failed: %s. Assigning all to cluster 0.", e)
            return np.zeros(len(embeddings), dtype=int)

    def _summarize_clusters(
        self,
        labels: np.ndarray,
        condition_names: list[str],
        embeddings: np.ndarray,
        organ_systems: list[str] | None = None,
    ) -> dict:
        """Build summary info for each cluster."""
        summaries = {}
        label_list = labels.tolist() if isinstance(labels, np.ndarray) else labels
        unique_labels = set(label_list)

        for label in unique_labels:
            indices = [i for i, l in enumerate(label_list) if l == label]
            cluster_names = [condition_names[i] for i in indices]

            # Find the most central condition (closest to centroid)
            if len(indices) > 1:
                cluster_embs = embeddings[indices]
                centroid = cluster_embs.mean(axis=0)
                dists = np.linalg.norm(cluster_embs - centroid, axis=1)
                representative = cluster_names[int(np.argmin(dists))]
            else:
                representative = cluster_names[0] if cluster_names else ""

            # Determine dominant organ system if available
            cluster_organs: list[str] = []
            dominant_organ = None
            if organ_systems:
                cluster_organs = [organ_systems[i] for i in indices if organ_systems[i]]
                if cluster_organs:
                    organ_counts = Counter(cluster_organs)
                    dominant_organ = organ_counts.most_common(1)[0][0]

            # Name the cluster
            if label == -1:
                label_name = "Noise"
            elif dominant_organ:
                label_name = f"{dominant_organ} Group"
            else:
                label_name = f"Cluster {label}"

            summaries[int(label)] = {
                "name": label_name,
                "size": len(indices),
                "representative": representative,
                "conditions": cluster_names,
                "organ_systems": list(set(cluster_organs)),
                "dominant_organ": dominant_organ,
            }

        return summaries
