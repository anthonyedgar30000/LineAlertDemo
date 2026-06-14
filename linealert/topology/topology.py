"""Machine topology container, loader, reports, and text visualization."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from linealert.topology.component import Component
from linealert.topology.dependency import Dependency


@dataclass(frozen=True)
class MachineTopology:
    """Machine structure independent from event relationships and cycles."""

    components: dict[str, Component]
    dependencies: list[Dependency]

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    def downstream_components(self, component_id: str) -> list[str]:
        adjacency = self.adjacency()
        _require_component(component_id, self.components)
        return sorted(adjacency.get(component_id, []))

    def upstream_components(self, component_id: str) -> list[str]:
        reverse_adjacency = self.reverse_adjacency()
        _require_component(component_id, self.components)
        return sorted(reverse_adjacency.get(component_id, []))

    def adjacency(self) -> dict[str, list[str]]:
        adjacency = {component_id: [] for component_id in self.components}
        for dependency in self.dependencies:
            adjacency.setdefault(dependency.upstream, []).append(dependency.downstream)
            adjacency.setdefault(dependency.downstream, [])
        return {key: sorted(values) for key, values in adjacency.items()}

    def reverse_adjacency(self) -> dict[str, list[str]]:
        reverse_adjacency = {component_id: [] for component_id in self.components}
        for dependency in self.dependencies:
            reverse_adjacency.setdefault(dependency.downstream, []).append(
                dependency.upstream
            )
            reverse_adjacency.setdefault(dependency.upstream, [])
        return {key: sorted(values) for key, values in reverse_adjacency.items()}

    def report(self) -> dict[str, object]:
        from linealert.topology.validator import validate_topology

        validation_report = validate_topology(self).as_dict()
        return {
            "component_count": self.component_count,
            "dependency_count": self.dependency_count,
            **validation_report,
        }

    def visualize(self) -> str:
        return visualize_topology(self)


def load_topology(config_path: str | Path) -> MachineTopology:
    """Load machine topology from JSON."""

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as topology_file:
        raw_topology = json.load(topology_file)
    if not isinstance(raw_topology, dict):
        raise ValueError(f"Topology config must be a JSON object: {path}")

    components = _parse_components(raw_topology.get("components"))
    dependencies = _parse_dependencies(raw_topology.get("dependencies"))
    return MachineTopology(components=components, dependencies=dependencies)


def visualize_topology(topology: MachineTopology) -> str:
    """Render each disconnected dependency chain as text."""

    adjacency = topology.adjacency()
    reverse_adjacency = topology.reverse_adjacency()
    roots = sorted(
        component_id
        for component_id in topology.components
        if not reverse_adjacency.get(component_id)
    )
    if not roots:
        roots = sorted(topology.components)

    rendered_chains = []
    visited_edges: set[tuple[str, str]] = set()
    for root in roots:
        rendered_chains.extend(
            _render_paths(
                current=root,
                adjacency=adjacency,
                path=[],
                visited_edges=visited_edges,
            )
        )

    if not rendered_chains:
        rendered_chains = [[component_id] for component_id in sorted(topology.components)]

    return "\n\n".join(_format_chain(chain) for chain in rendered_chains)


def topological_order(topology: MachineTopology) -> list[str]:
    """Return deterministic topological order or raise for circular dependencies."""

    adjacency = topology.adjacency()
    indegree = {component_id: 0 for component_id in adjacency}
    for upstream in adjacency:
        for downstream in adjacency[upstream]:
            indegree[downstream] += 1

    ready = deque(sorted(component for component, degree in indegree.items() if degree == 0))
    ordered: list[str] = []

    while ready:
        component_id = ready.popleft()
        ordered.append(component_id)
        for downstream in adjacency[component_id]:
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)

    if len(ordered) != len(indegree):
        raise ValueError("Topology contains circular dependencies")
    return ordered


def connected_components(topology: MachineTopology) -> list[list[str]]:
    """Return weakly connected component groups."""

    adjacency = topology.adjacency()
    reverse_adjacency = topology.reverse_adjacency()
    visited: set[str] = set()
    groups: list[list[str]] = []

    for component_id in sorted(topology.components):
        if component_id in visited:
            continue
        stack = [component_id]
        group: set[str] = set()
        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            stack.extend(adjacency.get(current, []))
            stack.extend(reverse_adjacency.get(current, []))
        known_group = {component for component in group if component in topology.components}
        visited.update(known_group)
        groups.append(_order_component_group(known_group, adjacency))

    return groups


def _order_component_group(
    group: set[str], adjacency: dict[str, list[str]]
) -> list[str]:
    indegree = {component_id: 0 for component_id in group}
    for upstream in group:
        for downstream in adjacency.get(upstream, []):
            if downstream in indegree:
                indegree[downstream] += 1

    ready = deque(sorted(component for component, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while ready:
        component_id = ready.popleft()
        ordered.append(component_id)
        for downstream in adjacency.get(component_id, []):
            if downstream not in indegree:
                continue
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)

    if len(ordered) != len(group):
        return sorted(group)
    return ordered


def _parse_components(raw_components: object) -> dict[str, Component]:
    if not isinstance(raw_components, list):
        raise ValueError("Topology config must contain a components list")

    components: dict[str, Component] = {}
    for index, raw_component in enumerate(raw_components, start=1):
        component = _parse_component(raw_component=raw_component, index=index)
        if component.component_id in components:
            raise ValueError(f"Duplicate component_id: {component.component_id}")
        components[component.component_id] = component
    return components


def _parse_component(raw_component: object, index: int) -> Component:
    if isinstance(raw_component, str):
        component_id = raw_component.strip()
        if not component_id:
            raise ValueError(f"Component {index} must not be empty")
        return Component(
            component_id=component_id,
            name=component_id,
            component_type="Unspecified",
        )

    if not isinstance(raw_component, dict):
        raise ValueError(f"Component {index} must be a string or object")

    component_id = _required_str(raw_component, "component_id", f"Component {index}")
    name = str(raw_component.get("name") or component_id)
    component_type = str(raw_component.get("type") or "Unspecified")
    parent_component = raw_component.get("parent_component")
    metadata = raw_component.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Component {index} metadata must be an object")

    return Component(
        component_id=component_id,
        name=name,
        component_type=component_type,
        parent_component=(
            str(parent_component) if parent_component is not None else None
        ),
        metadata=metadata,
    )


def _parse_dependencies(raw_dependencies: object) -> list[Dependency]:
    if not isinstance(raw_dependencies, list):
        raise ValueError("Topology config must contain a dependencies list")

    return [
        _parse_dependency(raw_dependency=raw_dependency, index=index)
        for index, raw_dependency in enumerate(raw_dependencies, start=1)
    ]


def _parse_dependency(raw_dependency: object, index: int) -> Dependency:
    context = f"Dependency {index}"
    if isinstance(raw_dependency, list):
        if len(raw_dependency) != 2:
            raise ValueError(f"{context} list form requires two component ids")
        return Dependency(
            upstream=str(raw_dependency[0]),
            downstream=str(raw_dependency[1]),
        )

    if not isinstance(raw_dependency, dict):
        raise ValueError(f"{context} must be a two-item list or object")

    return Dependency(
        upstream=_required_str(raw_dependency, "upstream", context),
        downstream=_required_str(raw_dependency, "downstream", context),
        metadata=(
            raw_dependency.get("metadata")
            if isinstance(raw_dependency.get("metadata"), dict)
            else None
        ),
    )


def _render_paths(
    current: str,
    adjacency: dict[str, list[str]],
    path: list[str],
    visited_edges: set[tuple[str, str]],
) -> list[list[str]]:
    next_path = [*path, current]
    downstream_components = adjacency.get(current, [])
    if not downstream_components:
        return [next_path]

    paths: list[list[str]] = []
    for downstream in downstream_components:
        edge = (current, downstream)
        if edge in visited_edges:
            continue
        visited_edges.add(edge)
        paths.extend(
            _render_paths(
                current=downstream,
                adjacency=adjacency,
                path=next_path,
                visited_edges=visited_edges,
            )
        )
    return paths or [next_path]


def _format_chain(chain: list[str]) -> str:
    lines: list[str] = []
    for index, component_id in enumerate(chain):
        if index > 0:
            lines.append("  ↓")
        lines.append(component_id)
    return "\n".join(lines)


def _required_str(raw_object: dict[str, object], field_name: str, context: str) -> str:
    value = raw_object.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{context} missing required field: {field_name}")
    return str(value)


def _require_component(
    component_id: str, components: dict[str, Component]
) -> None:
    if component_id not in components:
        raise ValueError(f"Unknown component: {component_id}")
