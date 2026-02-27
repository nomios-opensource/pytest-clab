"""Unit tests for ClabTopology class."""

from pytest_clab.nodes import ClabNodes


def test_given_topology_when_properties_accessed_then_returns_expected_values(topology) -> None:
    # Given topology
    # When properties accessed
    # Then returns expected values
    assert topology.name == "test-lab"
    assert topology.topology_path.name == "test.clab.yml"
    assert isinstance(topology.nodes, ClabNodes)
    assert len(topology.nodes) == 3


def test_given_topology_when_repr_called_then_returns_readable_string(topology) -> None:
    # Given topology
    # When __repr__() called
    result = repr(topology)

    # Then returns readable string
    assert "test-lab" in result
    assert "leaf1" in result


def test_given_command_when_topology_cmd_called_then_delegates_to_runner(topology) -> None:
    # Given command
    topology._runner.cmd.return_value = "saved"

    # When cmd() called
    result = topology.cmd("save")

    # Then delegates to runner
    assert result == "saved"
    topology._runner.cmd.assert_called_once_with("save", parse_json=False)
