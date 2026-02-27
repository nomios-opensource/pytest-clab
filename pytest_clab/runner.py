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

import json
import logging
import shlex
import shutil
import subprocess
import time
import typing as t
from pathlib import Path

from pytest_clab.exceptions import (
    CommandError,
    ContainerlabNotFoundError,
    DeploymentError,
    InspectError,
    NodeFailedError,
    TopologyNotFoundError,
)
from pytest_clab.models import ClabNode
from pytest_clab.settings import (
    CONTAINERLAB_EXECUTABLE,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_STARTUP_TIMEOUT,
    DEFAULT_SUDO,
)

logger = logging.getLogger(__name__)

_FAILED_STATES: frozenset[str] = frozenset({"exited", "dead"})
_STARTUP_POLL_INTERVAL_SECONDS: int = 5


class ClabRunner:
    """
    Wrapper for containerlab CLI operations.

    Handles deploy, destroy and inspect commands.
    """

    def __init__(
        self,
        topology_path: Path,
        sudo: bool = DEFAULT_SUDO,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
    ) -> None:
        """
        Initialize the runner.

        Args:
            topology_path: Path to the containerlab topology YAML file.
            sudo: Whether to run containerlab commands with sudo.
            command_timeout: Timeout in seconds for subprocess calls.

        Raises:
            ContainerlabNotFoundError: If containerlab CLI is not installed.
            TopologyNotFoundError: If the topology file doesn't exist.
        """
        self._topology_path = topology_path
        self._sudo = sudo
        self._command_timeout = command_timeout
        self._validate()

    @property
    def topology_path(self) -> Path:
        """Path to the containerlab topology YAML file."""
        return self._topology_path

    def _validate(self) -> None:
        """Validate that containerlab is installed and topology exists."""
        if shutil.which(CONTAINERLAB_EXECUTABLE) is None:
            raise ContainerlabNotFoundError(f"{CONTAINERLAB_EXECUTABLE} not found in PATH.")

        if not self._topology_path.exists():
            raise TopologyNotFoundError(f"Topology not found: {self._topology_path}")

    def _run(self, args: list[str], command_timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        """
        Execute a containerlab command.

        Args:
            args: Command arguments (e.g., ["deploy", "-t", "file.yml"]).
            command_timeout: Optional per-call timeout override.

        Returns:
            CompletedProcess with stdout/stderr captured.
        """
        effective_timeout = self._command_timeout if command_timeout is None else command_timeout
        cmd = [CONTAINERLAB_EXECUTABLE, *args]
        if self._sudo:
            cmd = ["sudo", *cmd]
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=effective_timeout)

    @staticmethod
    def _extract_short_name(full_name: str, lab_name: str) -> str:
        """Extract node short_name from container name and lab_name."""
        marker = f"{lab_name}-"
        if marker in full_name:
            return full_name.rsplit(marker, 1)[1]
        return full_name

    def is_deployed(self) -> bool:
        """
        Check if lab is currently deployed (containers exist for this topology).

        Returns:
            True if the lab has at least one container, False otherwise.
        """
        try:
            result = self._run(["inspect", "-t", str(self._topology_path), "-f", "json"])
            data: dict[str, list[dict[str, t.Any]]] = json.loads(result.stdout)
            containers = next(iter(data.values()), [])
            return len(containers) > 0
        except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired):
            return False

    def deploy(self) -> None:
        """
        Deploy a containerlab topology.

        Raises:
            DeploymentError: If deployment fails or times out.
        """
        try:
            logger.info(f"Deploying topology: {self._topology_path}")
            self._run(["deploy", "-t", str(self._topology_path), "--reconfigure"])
            logger.info(f"Successfully deployed: {self._topology_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Deploy failed for {self._topology_path}: {e.stderr}")
            raise DeploymentError(f"Deploy failed: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            logger.error(f"Deploy timed out for {self._topology_path} after {e.timeout}s")
            raise DeploymentError(f"Deploy timed out after {e.timeout}s") from e

    def destroy(self) -> None:
        """
        Destroy the topology and clean up.

        Note:
            Errors are logged as warnings but not raised, allowing cleanup
            of remaining labs to continue even if one fails.
        """
        try:
            logger.info(f"Destroying topology: {self._topology_path}")
            self._run(["destroy", "-t", str(self._topology_path), "--cleanup"])
            logger.info(f"Successfully destroyed: {self._topology_path}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Destroy failed for {self._topology_path}: {e.stderr}")
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Destroy timed out for {self._topology_path} after {e.timeout}s")

    def inspect(self, command_timeout: int | None = None) -> tuple[str, dict[str, ClabNode]]:
        """
        Inspect a running lab and return node information.

        Args:
            command_timeout: Optional per-call timeout override.

        Returns:
            Tuple of (lab_name, nodes_dict) where nodes_dict maps
            short_name to ClabNode.

        Raises:
            InspectError: If inspection fails, returns invalid JSON,
                          no containers found, or container data is malformed.
        """
        try:
            result = self._run(
                ["inspect", "-t", str(self._topology_path), "-f", "json"],
                command_timeout=command_timeout,
            )
        except subprocess.CalledProcessError as e:
            raise InspectError(f"Inspect failed: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise InspectError(f"Inspect timed out after {e.timeout}s") from e

        try:
            data: dict[str, list[dict[str, t.Any]]] = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise InspectError("Inspect returned invalid JSON.") from e

        # containerlab returns {"lab_name": [containers...]}
        containers = next(iter(data.values()), []) if data else []
        if not containers:
            raise InspectError("No containers found for topology.")

        nodes: dict[str, ClabNode] = {}
        lab_name: str = ""

        for container in containers:
            try:
                lab_name = container["lab_name"]
                short_name = self._extract_short_name(container["name"], lab_name)
                node = ClabNode.from_inspect(container, short_name)
                nodes[short_name] = node
            except KeyError as e:
                raise InspectError(f"Missing expected field in container data: {e}") from e

        return lab_name, nodes

    def wait_until_running(self, startup_timeout: int = DEFAULT_STARTUP_TIMEOUT) -> tuple[str, dict[str, ClabNode]]:
        """
        Wait for all nodes to reach state == "running".

        Polls containerlab inspect until all nodes are running, failing fast
        if any node enters a terminal state (exited, dead).

        Args:
            startup_timeout: Total wall-clock budget in seconds.

        Returns:
            Tuple of (lab_name, nodes_dict) where nodes_dict maps
            short_name to ClabNode.

        Raises:
            NodeFailedError: If any node enters a failed state.
            DeploymentError: If timeout is reached before all nodes are running.
        """
        deadline = time.monotonic() + startup_timeout
        last_error: InspectError | None = None
        last_states: dict[str, str] = {}

        logger.info(f"Waiting for nodes to reach running state (timeout={startup_timeout}s)...")

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                msg = f"Timed out after {startup_timeout}s waiting for nodes to reach running state."
                if last_states:
                    msg += f" Last observed states: {last_states}"
                if last_error:
                    msg += f" Last inspect error: {last_error}"
                raise DeploymentError(msg)

            # +1 avoids a zero-second timeout when remaining is fractional
            per_call_timeout = min(int(remaining) + 1, self._command_timeout)

            try:
                lab_name, nodes = self.inspect(command_timeout=per_call_timeout)
                last_error = None
            except InspectError as e:
                last_error = e
                logger.debug(f"Transient inspect error, retrying: {e}")
                time.sleep(min(_STARTUP_POLL_INTERVAL_SECONDS, remaining))
                continue

            last_states = {name: node.state for name, node in nodes.items()}

            # Check for failed nodes
            failed = {n: s for n, s in last_states.items() if s.lower() in _FAILED_STATES}
            if failed:
                raise NodeFailedError(f"Nodes entered failed state during startup: {failed}")

            # Check if all running
            not_running = {n: s for n, s in last_states.items() if s.lower() != "running"}
            if not not_running:
                logger.info("All nodes are running.")
                return lab_name, nodes

            logger.debug(f"Waiting for nodes: {not_running} (remaining={remaining:.0f}s)")
            time.sleep(min(_STARTUP_POLL_INTERVAL_SECONDS, remaining))

    def cmd(self, command: str, parse_json: bool = False) -> t.Any:
        """
        Execute any containerlab command.

        Args:
            command: Command string (e.g., "save -t /path/to/topo.yml").
            parse_json: If True, parse stdout as JSON.

        Returns:
            Command stdout as string. If stdout is empty, returns stderr
            (containerlab writes INFO logs to stderr on some commands).
            If parse_json=True, returns parsed JSON from stdout.

        Raises:
            ValueError: If command is empty.
            CommandError: If command execution fails or JSON parsing fails.
        """
        if not command or not command.strip():
            raise ValueError("cmd() requires a non-empty command string")

        args = shlex.split(command)

        try:
            result = self._run(args)
        except subprocess.CalledProcessError as e:
            raise CommandError(f"Command '{args[0]}' failed: {e.stderr or 'unknown error'}") from e
        except subprocess.TimeoutExpired as e:
            raise CommandError(f"Command '{args[0]}' timed out after {e.timeout}s") from e

        if parse_json:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise CommandError("Command returned invalid JSON.") from e

        return result.stdout if result.stdout else result.stderr
