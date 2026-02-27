# pytest-clab

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/nomios-open-source/pytest-clab/tests.yml?branch=main)
![Codecov](https://img.shields.io/codecov/c/github/nomios-open-source/pytest-clab)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pytest-clab)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pytest-clab)
![GitHub License](https://img.shields.io/github/license/nomios-open-source/pytest-clab)

`pytest-clab` is authored by [Thomas Bamihas](https://github.com/tbamihas), governed as a [benevolent dictatorship](CODE_OF_CONDUCT.md), and distributed under the [Apache 2.0 license](LICENSE).

## Introduction

While containerlab simplifies spinning up network topologies, integrating it into test workflows still requires boilerplate for deployment, teardown, and node interaction. This plugin provides a convenient pytest fixture to manage containerlab topologies with automatic lifecycle management.

## Features

- **Lab lifecycle management**: Deploy and destroy containerlab topologies directly from pytest.
- **Multiple lab support**: Interact with multiple labs within a single pytest session, for tests that depend on more than one topology.
- **Topology readiness checks**: Verify dependent labs are ready before running tests.
- **Dynamic node inventory**: Retrieve node addresses and connection parameters at test runtime instead of hardcoding them in tests.
- **Containerlab CLI access**: Run containerlab commands from tests for operations not covered by plugin helpers.

## Installation

```bash
pip install pytest-clab
```

**Requirements:** `containerlab` CLI must be installed and in PATH.

## Quickstart

```python
@pytest.fixture(scope="session")
def lab(clab):
    return clab("topology.clab.yaml")

@pytest.mark.parametrize("node_name", ["node1", "node2"])
def test_mgmt_interface_status(lab, node_name):
    # GIVEN a lab node
    node = lab.nodes[node_name]

    # GIVEN netmiko params
    params = {
        "host": node.ipv4_address,
        "username": os.getenv("SSH_USERNAME"),
        "password": os.getenv("SSH_PASSWORD"),
        "device_type": "nokia_srl",
    }

    # WHEN fetching mgmt status
    with netmiko.ConnectHandler(**params) as conn:
        output = conn.send_command("show interface mgmt0 brief")

    # THEN expect mgmt0 to be up
    assert "up" in output
```

## Working with Topologies and Nodes

### ClabTopology

The `clab` fixture is a factory that creates `ClabTopology` instances.

**Properties:**
- `name` - Lab name as reported by containerlab
- `topology_path` - Path to the topology YAML file
- `nodes` - Collection of nodes

**Methods:**
- `cmd(command, parse_json=False)` - Execute any containerlab command, optionally parse JSON output

```python
output = lab.cmd("inspect -f json", parse_json=True)
```

### Node Startup Readiness

The plugin automatically polls `containerlab inspect` and returns only after all nodes report `state: "running"`.

- `command_timeout` controls timeout per containerlab CLI call.
- `startup_timeout` controls total startup polling budget.

Service-level readiness (SSH, NETCONF, gNMI, app-level) checks are environment-specific and performed in test logic.

### ClabNodes

The `nodes` property is a collection that supports flexible access patterns.

**Methods:**
- `lab.nodes["name"]` - Access a node by short name
- `"name" in lab.nodes` - Check if a node exists
- `len(lab.nodes)` - Get the number of nodes
- `for node in lab.nodes` - Iterate over all nodes
- `filter_by_kind(kind)` - Filter nodes by kind

```python
for node in lab.nodes:
    print(node.short_name, node.ipv4_address)
```

### ClabNode

Each node is an immutable dataclass with the following attributes.

**Attributes:**
- `short_name` - Node name without lab prefix (e.g., "leaf1")
- `name` - Full container name (e.g., "clab-mylab-leaf1")
- `lab_name` - Name of the lab
- `kind` - Node kind (e.g., "linux", "nokia_srlinux")
- `image` - Container image
- `state` - Container state (e.g., "running")
- `status` - Container status from containerlab (e.g., "healthy")
- `ipv4_address` - Management IPv4 address
- `ipv6_address` - Management IPv6 address
- `container_id` - Docker container ID
- `properties` - Dictionary containing additional containerlab node properties not listed above

```python
node = lab.nodes["leaf1"]
print(f"{node.short_name} ({node.kind}): {node.ipv4_address}")
```

## Examples

<details>
<summary>Keep Running Mode</summary>

```python
@pytest.fixture(scope="session")
def lab(clab):
    return clab("topology.clab.yml", keep_running=True)
```
</details>

<details>
<summary>JSON Output</summary>

```python
def test_json_output(lab):
    result = lab.cmd("inspect -f json", parse_json=True)
    assert isinstance(result, dict)
```
</details>

<details>
<summary>Filter by Node Kind</summary>

```python
def test_filter_nodes(lab):
    srlinux_nodes = lab.nodes.filter_by_kind("nokia_srlinux")
    linux_nodes = lab.nodes.filter_by_kind("linux")
    assert len(srlinux_nodes) + len(linux_nodes) == len(lab.nodes)
```
</details>

<details>
<summary>Dynamic Validation Example</summary>

This example uses [subtests](https://docs.pytest.org/en/stable/how-to/subtests.html) for per-peer test reporting.

```python
def test_bgp_neighbors(lab, subtests):
    node = lab.nodes["router1"]
    # Use any library to connect to the node (e.g., ncclient, scrapli, netmiko)
    with connect(host=node.ipv4_address, ...) as conn:
        neighbors = conn.get(filter=BGP_NEIGHBOR_FILTER).data_xml

    for neighbor in neighbors:
        with subtests.test(peer=neighbor.find("peer-address").text):
            assert neighbor.find("state").text == "established"
```
</details>

## Configuration

### Environment Variables

**`CONTAINERLAB_EXECUTABLE`**
Path to containerlab executable
(default: `containerlab`)

```bash
CONTAINERLAB_EXECUTABLE=/usr/local/bin/clab pytest
```

### Fixture Parameters

**`topology`:**
Path to containerlab topology YAML file
(required)

```python
lab = clab("topology.clab.yml")
```

**`sudo`:**
Run containerlab commands with sudo
(default: `False`)

```python
lab = clab("topology.clab.yml", sudo=True)
```

**`keep_running`:**
Keep lab running at session end
(default: `False`)

```python
lab = clab("topology.clab.yml", keep_running=True)
```

**`command_timeout`:**
Timeout in seconds for each containerlab command
(default: `300`)

```python
lab = clab("topology.clab.yml", command_timeout=600)
```

**`startup_timeout`:**
Timeout in seconds for startup-state polling
(default: `30`)

```python
lab = clab("topology.clab.yml", startup_timeout=60)
```

## Exceptions

The plugin provides a hierarchy of exceptions for error handling:

- **`ClabError`**: Base exception for all pytest-clab errors
- **`TopologyNotFoundError`**: Topology file does not exist
- **`ContainerlabNotFoundError`**: containerlab executable not found in PATH
- **`DeploymentError`**: Topology deployment failed
- **`InspectError`**: Failed to inspect running topology
- **`CommandError`**: A containerlab command failed
- **`NodeFailedError`**: A node entered a terminal failed state during startup

## Versioning

Releases will follow semantic versioning (major.minor.patch). Before 1.0.0, breaking changes can be included in a minor release, therefore we highly recommend pinning this package.

## Contributing

Suggest a [feature](https://github.com/nomios-open-source/pytest-clab/issues/new?labels=enhancement) or report a [bug](https://github.com/nomios-open-source/pytest-clab/issues/new?labels=bug). Read our developer [guide](CONTRIBUTING.md).

## License

pytest-clab is distributed under the Apache 2.0 [license](LICENSE).
