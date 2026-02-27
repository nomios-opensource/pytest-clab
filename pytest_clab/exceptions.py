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


class ClabError(Exception):
    """Base exception for all pytest-clab errors."""


class ContainerlabNotFoundError(ClabError):
    """Raised when containerlab CLI is not found in PATH."""


class TopologyNotFoundError(ClabError):
    """Raised when the topology file does not exist."""


class DeploymentError(ClabError):
    """Raised when lab deployment fails."""


class InspectError(ClabError):
    """Raised when lab inspection fails."""


class CommandError(ClabError):
    """Raised when a containerlab command fails."""


class NodeFailedError(DeploymentError):
    """Raised when a node enters a terminal state (exited, dead) during startup."""
