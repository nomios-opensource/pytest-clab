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

from collections.abc import Callable, Iterator

import pytest

from pytest_clab.manager import ClabManager
from pytest_clab.topology import ClabTopology


@pytest.fixture(scope="session")
def clab() -> Iterator[Callable[..., ClabTopology]]:
    """
    Factory fixture for containerlab topologies.

    Deploys topologies and returns ClabTopology instances.
    Labs are destroyed at session end unless keep_running=True.

    A startup gate runs for every lab and returns only when all nodes
    report state "running".

    Usage:
        def test_something(clab):
            lab = clab("topology.clab.yml")
            assert lab.nodes["router1"].state == "running"

        # Keep lab running after tests
        def test_dev(clab):
            lab = clab("topology.clab.yml", keep_running=True)

    Args (to the returned callable):
        topology: Path to containerlab topology YAML file.
        sudo: If True, run containerlab with sudo. (default: False).
        keep_running: If True, lab won't be destroyed at session end.
        command_timeout: Timeout in seconds for each containerlab command. (default: 300).
        startup_timeout: Timeout in seconds for startup state polling. (default: 30).

    Yields:
        Callable that creates ClabTopology instances.
    """
    manager = ClabManager()
    yield manager.create
    manager.cleanup()
