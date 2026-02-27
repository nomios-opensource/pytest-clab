"""
Copyright 2026 Nomios UK&I

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from collections.abc import Iterator

from pytest_clab.models import ClabNode


class ClabNodes:
    """A collection of containerlab nodes."""

    def __init__(self, nodes: dict[str, ClabNode]) -> None:
        """Initialize the nodes collection."""
        self._nodes = nodes

    def __getitem__(self, name: str) -> ClabNode:
        """Get a node by short name."""
        if name not in self._nodes:
            available = ", ".join(sorted(self._nodes.keys()))
            raise KeyError(f"Node '{name}' not found. Available: {available}")
        return self._nodes[name]

    def __contains__(self, name: object) -> bool:
        """Check if a node exists in the collection."""
        return name in self._nodes

    def __len__(self) -> int:
        """Return the number of nodes in the collection."""
        return len(self._nodes)

    def __iter__(self) -> Iterator[ClabNode]:
        """Iterate over ClabNode objects."""
        return iter(self._nodes.values())

    def __repr__(self) -> str:
        """Return a string representation of the collection."""
        return f"ClabNodes({list(self._nodes.keys())})"

    def filter_by_kind(self, kind: str) -> "ClabNodes":
        """Get all nodes matching a specific kind."""
        filtered = {name: node for name, node in self._nodes.items() if node.kind == kind}
        return ClabNodes(filtered)
