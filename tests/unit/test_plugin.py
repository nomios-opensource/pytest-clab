"""Unit tests for pytest plugin."""

import json
from unittest.mock import Mock, patch


def test_given_topology_file_when_clab_fixture_called_then_returns_topology(tmp_path, clab) -> None:
    # Given topology file
    topology_file = tmp_path / "test.clab.yml"
    topology_file.write_text("name: test-lab")
    mock_result = Mock()
    mock_result.stdout = json.dumps(
        {
            "unit-test-lab": [
                {
                    "name": "clab-unit-test-lab-r1",
                    "lab_name": "unit-test-lab",
                    "container_id": "abc123",
                    "image": "alpine:latest",
                    "kind": "linux",
                    "state": "running",
                    "ipv4_address": "172.20.20.2/24",
                }
            ]
        }
    )

    # When clab fixture called
    with patch("subprocess.run", return_value=mock_result):
        with patch("shutil.which", return_value="/usr/bin/containerlab"):
            lab = clab(topology_file)

    # Then returns topology
    assert lab.name == "unit-test-lab"
    assert "r1" in lab.nodes
