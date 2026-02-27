"""End-to-end tests for the clab fixture."""

from pathlib import Path

import pytest


@pytest.mark.e2e
def test_given_topology_when_clab_called_then_deploys_and_returns_topology(
    clab,
    clab_topology: Path,
) -> None:
    # Given topology
    # When clab() called
    lab = clab(clab_topology)

    # Then deploys and returns topology
    assert lab.name == "e2e-test-lab"
    assert len(lab.nodes) == 2
    assert "node1" in lab.nodes
    assert "node2" in lab.nodes
    assert lab.nodes["node1"].state == "running"


@pytest.mark.e2e
def test_given_deployed_lab_when_node_accessed_then_returns_node_properties(
    clab,
    clab_topology: Path,
) -> None:
    # Given deployed lab
    lab = clab(clab_topology)

    # When node accessed
    node = lab.nodes["node1"]

    # Then returns node properties
    assert node.short_name == "node1"
    assert node.lab_name == "e2e-test-lab"
    assert node.kind == "linux"
    assert node.image == "alpine:latest"
    assert node.ipv4_address is not None


@pytest.mark.e2e
def test_given_deployed_lab_when_iterating_nodes_then_yields_all_nodes(
    clab,
    clab_topology: Path,
) -> None:
    # Given deployed lab
    lab = clab(clab_topology)

    # When iterating nodes
    node_names = [node.short_name for node in lab.nodes]

    # Then yields all nodes
    assert sorted(node_names) == ["node1", "node2"]


@pytest.mark.e2e
def test_given_deployed_lab_when_filter_by_kind_called_then_returns_matching_nodes(
    clab,
    clab_topology: Path,
) -> None:
    # Given deployed lab
    lab = clab(clab_topology)

    # When filter_by_kind() called
    linux_nodes = lab.nodes.filter_by_kind("linux")

    # Then returns matching nodes
    assert len(linux_nodes) == 2
    assert all(node.kind == "linux" for node in linux_nodes)


@pytest.mark.e2e
def test_given_deployed_lab_when_cmd_called_then_executes_containerlab_command(
    clab,
    clab_topology: Path,
) -> None:
    # Given deployed lab
    lab = clab(clab_topology)

    # When cmd() called
    result = lab.cmd("version")

    # Then executes containerlab command
    assert "containerlab" in result.lower() or "version" in result.lower()


@pytest.mark.e2e
def test_given_deployed_lab_when_cmd_with_parse_json_called_then_returns_parsed_json(
    clab,
    clab_topology: Path,
) -> None:
    # Given deployed lab
    lab = clab(clab_topology)

    # When cmd() with parse_json called
    result = lab.cmd("version -j", parse_json=True)

    # Then returns parsed JSON
    assert isinstance(result, dict)
    assert "version" in result


@pytest.mark.e2e
def test_given_topology_when_custom_timeout_used_then_respects_parameter(
    clab,
    clab_topology: Path,
) -> None:
    # Given topology
    # When clab() called with custom command timeout
    lab = clab(clab_topology, command_timeout=60)

    # Then lab deploys successfully
    assert lab.name == "e2e-test-lab"
    assert len(lab.nodes) == 2


@pytest.mark.e2e
def test_given_topology_when_custom_startup_timeout_used_then_respects_parameter(
    clab,
    clab_topology: Path,
) -> None:
    # Given topology
    # When clab() called with custom startup timeout
    lab = clab(clab_topology, startup_timeout=60)

    # Then lab deploys successfully
    assert lab.name == "e2e-test-lab"
    assert len(lab.nodes) == 2
