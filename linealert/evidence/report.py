"""Evidence Fusion report formatting."""

from __future__ import annotations

from linealert.evidence.evidence_fusion import FusedEvidencePackage


def generate_evidence_fusion_report(
    fused_package: FusedEvidencePackage,
) -> dict[str, object]:
    """Return a JSON-serializable fused evidence report."""

    return fused_package.as_dict()


def format_evidence_fusion_report(fused_package: FusedEvidencePackage) -> str:
    """Render an observation-only evidence fusion summary."""

    lines = [
        "EVIDENCE SUMMARY",
        "",
        f"Evidence Density: {fused_package.evidence_density} observations",
        f"Sources Contributing: {fused_package.sources_contributing}",
        "",
    ]

    for cluster in fused_package.observation_clusters:
        lines.extend(
            [
                "Observation Cluster:",
                cluster.cluster,
                "",
                "Supporting Evidence:",
                "",
            ]
        )
        for source in sorted(cluster.source_distribution):
            lines.append(f"{source}:")
            for item in cluster.supporting_evidence:
                if item.source == source:
                    lines.append(f"- {item.observation}")
            lines.append("")

    lines.extend(
        [
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
        ]
    )
    return "\n".join(lines).rstrip()
