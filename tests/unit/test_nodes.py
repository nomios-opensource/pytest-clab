"""Unit tests for ClabNodes collection class."""

import pytest

from pytest_clab.models import ClabNode
from pytest_clab.nodes import ClabNodes


def test_given_missing_node_when_getitem_called_then_raises_keyerror_with_available_nodes(
    three_nodes: ClabNodes,
) -> None:
    # Given missing node
    # When __getitem__() called
    # Then raises KeyError with available nodes
    with pytest.raises(KeyError, match="Node 'missing' not found") as exc_info:
        three_nodes["missing"]
    assert "Available:" in str(exc_info.value)


def test_given_matching_nodes_when_filter_by_kind_called_then_returns_matches(
    three_nodes: ClabNodes,
) -> None:
    # Given matching nodes
    # When filter_by_kind() called
    result = three_nodes.filter_by_kind("nokia_srlinux")

    # Then returns ClabNodes with matches
    assert isinstance(result, ClabNodes)
    assert len(result) == 2
    assert all(node.kind == "nokia_srlinux" for node in result)
    assert result["leaf1"].kind == "nokia_srlinux"


def test_given_nodes_when_repr_called_then_returns_expected_string(
    three_nodes: ClabNodes,
) -> None:
    # Given nodes
    # When __repr__() called
    result = repr(three_nodes)

    # Then returns expected string
    assert result == "ClabNodes(['leaf1', 'leaf2', 'spine1'])"


@pytest.mark.parametrize(
    "ipv4_input, ipv6_input, expected_ipv4, expected_ipv6",
    [
        ("172.20.20.2/24", "3fff:172:20:20::2/64", "172.20.20.2", "3fff:172:20:20::2"),
        ("10.0.0.1/32", "fe80::1/128", "10.0.0.1", "fe80::1"),
        ("172.20.20.2", "3fff:172:20:20::2", "172.20.20.2", "3fff:172:20:20::2"),
        (None, None, None, None),
        ("N/A", "N/A", None, None),
    ],
)
def test_given_inspect_data_with_cidr_when_from_inspect_called_then_cidr_is_stripped(
    ipv4_input, ipv6_input, expected_ipv4, expected_ipv6
) -> None:
    # Given inspect data with CIDR notation
    container = {
        "name": "clab-test-node1",
        "lab_name": "test",
        "container_id": "abc123",
        "image": "alpine:latest",
        "kind": "linux",
        "state": "running",
        "status": "healthy",
        "ipv4_address": ipv4_input,
        "ipv6_address": ipv6_input,
    }

    # When from_inspect() called
    node = ClabNode.from_inspect(container, short_name="node1")

    # Then CIDR is stripped from IP addresses
    assert node.ipv4_address == expected_ipv4
    assert node.ipv6_address == expected_ipv6
