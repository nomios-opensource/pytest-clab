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

import typing as t
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClabNode:
    """
    Immutable representation of a containerlab node.

    Attributes:
        name: Full container name (e.g., "clab-mylab-leaf1").
        short_name: Node name without lab prefix (e.g., "leaf1").
        lab_name: Name of the lab this node belongs to.
        container_id: Docker container ID.
        image: Container image used for this node.
        kind: Node kind (e.g., "nokia_srlinux", "arista_ceos").
        state: Container state (e.g., "running", "exited").
        status: Container status string (e.g., "Up 5 minutes", "healthy", "unhealthy", "health: starting").
        ipv4_address: Management IPv4 address (CIDR notation stripped).
        ipv6_address: Management IPv6 address (CIDR notation stripped).
        properties: Additional containerlab node properties not explicitly modeled.
    """

    name: str
    short_name: str
    lab_name: str
    container_id: str
    image: str
    kind: str
    state: str
    status: str
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    properties: dict[str, t.Any] = field(default_factory=dict)

    @classmethod
    def from_inspect(
        cls,
        container: dict[str, t.Any],
        short_name: str,
    ) -> "ClabNode":
        """
        Create a ClabNode from containerlab inspect output.

        Args:
            container: Raw container data from containerlab inspect.
            short_name: Extracted short name for the node.

        Returns:
            ClabNode instance.
        """
        known_fields = {
            "name",
            "lab_name",
            "container_id",
            "image",
            "kind",
            "state",
            "status",
            "ipv4_address",
            "ipv6_address",
        }
        properties = {k: v for k, v in container.items() if k not in known_fields}

        # Strip CIDR notation from IP addresses; normalize "N/A" to None
        ip_fields: dict[str, str | None] = {}
        for attr in ("ipv4_address", "ipv6_address"):
            value = container.get(attr)
            if not value or value == "N/A":
                ip_fields[attr] = None
            elif "/" in value:
                ip_fields[attr] = value.split("/")[0]
            else:
                ip_fields[attr] = value

        return cls(
            name=container["name"],
            short_name=short_name,
            lab_name=container["lab_name"],
            container_id=container["container_id"],
            image=container["image"],
            kind=container["kind"],
            state=container["state"],
            status=container.get("status", ""),
            ipv4_address=ip_fields["ipv4_address"],
            ipv6_address=ip_fields["ipv6_address"],
            properties=properties,
        )
