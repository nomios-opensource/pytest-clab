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

import typing as t
from pathlib import Path

from pytest_clab.models import ClabNode
from pytest_clab.nodes import ClabNodes

if t.TYPE_CHECKING:
    from pytest_clab.runner import ClabRunner  # pragma: no cover


class ClabTopology:
    """
    A deployed containerlab topology.

    Provides access to topology metadata and nodes. Node operations
    (iteration, filtering, containment checks) are accessed via the
    `nodes` property.
    """

    def __init__(
        self,
        name: str,
        topology_path: Path,
        nodes: dict[str, ClabNode],
        runner: "ClabRunner",
    ) -> None:
        """
        Initialize the topology.

        Args:
            name: Lab name as reported by containerlab.
            topology_path: Path to the containerlab topology YAML file.
            nodes: Dictionary mapping short names to ClabNode instances.
            runner: ClabRunner instance for executing commands.
        """
        self._name = name
        self._topology_path = topology_path
        self._nodes = ClabNodes(nodes)
        self._runner = runner

    @property
    def name(self) -> str:
        """Lab name as reported by containerlab."""
        return self._name

    @property
    def topology_path(self) -> Path:
        """Path to the containerlab topology YAML file."""
        return self._topology_path

    @property
    def nodes(self) -> ClabNodes:
        """Collection of nodes in the topology."""
        return self._nodes

    def __repr__(self) -> str:
        """Return a string representation of the topology."""
        return f"ClabTopology(name='{self._name}', nodes={[node.short_name for node in self._nodes]})"

    def cmd(self, command: str, parse_json: bool = False) -> t.Any:
        """
        Execute any containerlab command.

        Use self.topology_path to include the topology file in commands that require it.

        Args:
            command: Command string (e.g., f"save -t {self.topology_path}").
            parse_json: If True, parse stdout as JSON.

        Returns:
            Command stdout as string, or parsed JSON if parse_json=True.

        Raises:
            CommandError: If command execution fails.
        """
        return self._runner.cmd(command, parse_json=parse_json)
