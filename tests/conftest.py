"""Test fixtures and helpers."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pytest_clab.models import ClabNode
from pytest_clab.nodes import ClabNodes
from pytest_clab.runner import ClabRunner
from pytest_clab.topology import ClabTopology


def node(**overrides) -> ClabNode:
    """A ClabNode instance with defaults."""
    defaults = {
        "name": "clab-test-leaf1",
        "short_name": "leaf1",
        "lab_name": "test",
        "container_id": "abc123",
        "image": "alpine:latest",
        "kind": "linux",
        "state": "running",
        "status": "Up 5 minutes",
    }
    return ClabNode(**{**defaults, **overrides})


def _make_nodes_dict() -> dict[str, ClabNode]:
    """3-node dict for testing."""
    return {
        "leaf1": node(name="clab-test-leaf1", short_name="leaf1", kind="nokia_srlinux"),
        "leaf2": node(name="clab-test-leaf2", short_name="leaf2", kind="nokia_srlinux"),
        "spine1": node(name="clab-test-spine1", short_name="spine1", kind="nokia_sros"),
    }


@pytest.fixture
def three_nodes() -> ClabNodes:
    """3-node ClabNodes collection for testing."""
    return ClabNodes(_make_nodes_dict())


def inspect_json(
    status: str = "Up 5 minutes",
    node_name: str = "node1",
    lab: str = "test",
) -> str:
    """Create containerlab inspect JSON output."""
    return json.dumps(
        {
            lab: [
                {
                    "lab_name": lab,
                    "name": f"clab-{lab}-{node_name}",
                    "container_id": "abc123",
                    "image": "alpine:latest",
                    "kind": "linux",
                    "state": "running",
                    "status": status,
                    "ipv4_address": "172.20.20.2/24",
                }
            ]
        }
    )


def inspect_json_with_state(
    state: str = "running",
    status: str = "Up 5 minutes",
    node_name: str = "node1",
    lab: str = "test",
) -> str:
    """Create containerlab inspect JSON output with configurable state."""
    return json.dumps(
        {
            lab: [
                {
                    "lab_name": lab,
                    "name": f"clab-{lab}-{node_name}",
                    "container_id": "abc123",
                    "image": "alpine:latest",
                    "kind": "linux",
                    "state": state,
                    "status": status,
                    "ipv4_address": "172.20.20.2/24",
                }
            ]
        }
    )


def inspect_json_multi(nodes: list[dict[str, str]], lab: str = "test") -> str:
    """Create containerlab inspect JSON with multiple nodes."""
    containers = []
    for n in nodes:
        containers.append(
            {
                "lab_name": lab,
                "name": f"clab-{lab}-{n['name']}",
                "container_id": "abc123",
                "image": "alpine:latest",
                "kind": n.get("kind", "linux"),
                "state": n.get("state", "running"),
                "status": n.get("status", ""),
                "ipv4_address": "172.20.20.2/24",
            }
        )
    return json.dumps({lab: containers})


@pytest.fixture
def mock_runner() -> MagicMock:
    """Mock ClabRunner for testing code that uses a runner."""
    mock = MagicMock(spec=ClabRunner)
    mock.is_deployed.return_value = False
    mock.wait_until_running.return_value = ("test", {})
    return mock


@pytest.fixture
def topology_path(tmp_path: Path) -> Path:
    """Topology file path for testing."""
    topo_path = tmp_path / "test.clab.yml"
    topo_path.touch()
    return topo_path


@pytest.fixture
def runner(topology_path: Path, mock_subprocess_run) -> ClabRunner:
    """ClabRunner for testing the ClabRunner class itself."""
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        return ClabRunner(topology_path, command_timeout=300)


@pytest.fixture
def topology(tmp_path: Path, mock_runner: MagicMock) -> ClabTopology:
    """ClabTopology with 3 nodes and mock runner."""
    return ClabTopology(
        name="test-lab",
        topology_path=tmp_path / "test.clab.yml",
        nodes=_make_nodes_dict(),
        runner=mock_runner,
    )


@pytest.fixture
def mock_subprocess_run():
    """Patch subprocess.run with a successful CompletedProcess.

    Yields the mock for keeping the context manager active
    during the test.
    """
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        yield mock_run
