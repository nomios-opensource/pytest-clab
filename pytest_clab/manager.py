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

import logging
from pathlib import Path

from pytest_clab.runner import ClabRunner
from pytest_clab.settings import DEFAULT_COMMAND_TIMEOUT, DEFAULT_STARTUP_TIMEOUT, DEFAULT_SUDO
from pytest_clab.topology import ClabTopology

logger = logging.getLogger(__name__)


class ClabManager:
    """
    Manages containerlab topology lifecycle.

    Handles deployment, tracking, and cleanup of multiple topologies.
    """

    def __init__(self) -> None:
        """Initialize the manager."""
        self._labs: list[tuple[ClabRunner, bool]] = []

    def create(
        self,
        topology: str | Path,
        keep_running: bool = False,
        sudo: bool = DEFAULT_SUDO,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
        startup_timeout: int = DEFAULT_STARTUP_TIMEOUT,
    ) -> ClabTopology:
        """
        Create and deploy a containerlab topology.

        Args:
            topology: Path to containerlab topology YAML file.
            keep_running: If True, lab won't be destroyed during cleanup.
            sudo: Whether to run containerlab commands with sudo.
            command_timeout: Timeout in seconds for each containerlab subprocess call.
            startup_timeout: Total timeout in seconds while waiting for nodes to reach running state.

        Returns:
            ClabTopology instance for the deployed lab.
        """
        path = Path(topology).expanduser().resolve()
        runner = ClabRunner(path, sudo=sudo, command_timeout=command_timeout)

        already_deployed = runner.is_deployed()

        # Track with forced cleanup before any mutations
        self._labs.append((runner, False))

        try:
            if not already_deployed:
                runner.deploy()

            lab_name, nodes = runner.wait_until_running(startup_timeout=startup_timeout)
        except Exception:
            if already_deployed:
                # Don't destroy a lab we didn't create
                self._labs.pop()
            raise

        # On success apply user's keep_running bool
        self._labs[-1] = (runner, keep_running)
        lab = ClabTopology(lab_name, path, nodes, runner)
        logger.debug(f"Tracking lab: {lab_name} (keep_running={keep_running})")

        return lab

    def cleanup(self) -> None:
        """Destroy all tracked labs in reverse order (unless keep_running)."""
        logger.info(f"Cleaning up {len(self._labs)} tracked lab(s)")
        for runner, keep_running in reversed(self._labs):
            if not keep_running:
                try:
                    runner.destroy()
                except Exception:
                    logger.exception(f"Unexpected error destroying lab: {runner.topology_path}")
            else:
                logger.debug("Skipping cleanup for lab (keep_running=True)")
