"""Conftest for e2e tests."""

from pathlib import Path

import pytest


@pytest.fixture
def clab_topology(tmp_path: Path) -> Path:
    """Two-node linux topology for e2e tests."""
    topology = tmp_path / "e2e.clab.yml"
    topology.write_text("""\
name: e2e-test-lab
topology:
  nodes:
    node1:
      kind: linux
      image: alpine:latest
    node2:
      kind: linux
      image: alpine:latest
""")
    return topology
