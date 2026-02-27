"""Unit tests for ClabRunner class."""

import json
import logging
import subprocess
from unittest.mock import patch

import pytest

from pytest_clab.exceptions import (
    CommandError,
    ContainerlabNotFoundError,
    DeploymentError,
    InspectError,
    NodeFailedError,
    TopologyNotFoundError,
)
from pytest_clab.runner import ClabRunner
from tests.conftest import inspect_json, inspect_json_multi, inspect_json_with_state


def test_given_containerlab_not_installed_when_runner_created_then_raises_error(tmp_path) -> None:
    # Given containerlab not installed
    topology_file = tmp_path / "test.clab.yml"
    topology_file.touch()

    # When runner created
    # Then raises error
    with patch("shutil.which", return_value=None):
        with pytest.raises(ContainerlabNotFoundError, match="not found in PATH"):
            ClabRunner(topology_file)


def test_given_topology_file_missing_when_runner_created_then_raises_error(tmp_path) -> None:
    # Given topology file missing
    missing_file = tmp_path / "missing.clab.yml"

    # When runner created
    # Then raises error
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        with pytest.raises(TopologyNotFoundError, match="Topology not found"):
            ClabRunner(missing_file)


def test_given_valid_topology_when_topology_path_accessed_then_returns_path(runner, topology_path) -> None:
    # Given valid runner
    # When topology_path accessed
    result = runner.topology_path

    # Then returns the path
    assert result == topology_path


def test_given_sudo_true_when_run_called_then_executes_with_sudo(topology_path, mock_subprocess_run) -> None:
    # Given sudo true
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        sudo_runner = ClabRunner(topology_path, sudo=True)

    # When run called
    sudo_runner._run(["inspect", "-t", str(topology_path)])

    # Then executes with sudo
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    assert call_args[0] == "sudo"
    assert "inspect" in call_args


def test_given_sudo_false_when_run_called_then_executes_without_sudo(topology_path, mock_subprocess_run) -> None:
    # Given sudo false
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        no_sudo_runner = ClabRunner(topology_path, sudo=False)

    # When run called
    no_sudo_runner._run(["inspect", "-t", str(topology_path)])

    # Then executes without sudo
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    assert "sudo" not in call_args


@pytest.mark.parametrize("state", ["running", "starting"])
def test_given_containers_exist_when_is_deployed_called_then_returns_true(runner, mock_subprocess_run, state) -> None:
    # Given containers exist
    output = json.dumps({"test": [{"name": "clab-test-node1", "state": state}]})
    mock_subprocess_run.return_value.stdout = output

    # When is_deployed() called
    result = runner.is_deployed()

    # Then returns True
    assert result is True


def test_given_empty_containers_when_is_deployed_called_then_returns_false(runner, mock_subprocess_run) -> None:
    # Given empty containers
    mock_subprocess_run.return_value.stdout = json.dumps({"test": []})

    # When is_deployed() called
    result = runner.is_deployed()

    # Then returns False
    assert result is False


def test_given_invalid_json_when_is_deployed_called_then_returns_false(runner, mock_subprocess_run) -> None:
    # Given invalid JSON output
    mock_subprocess_run.return_value.stdout = "not-json"

    # When is_deployed() called
    result = runner.is_deployed()

    # Then returns False
    assert result is False


def test_given_inspect_fails_when_is_deployed_called_then_returns_false(runner, mock_subprocess_run) -> None:
    # Given inspect fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "containerlab")

    # When is_deployed() called
    result = runner.is_deployed()

    # Then returns False
    assert result is False


def test_given_inspect_times_out_when_is_deployed_called_then_returns_false(runner, mock_subprocess_run) -> None:
    # Given inspect times out
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=300)

    # When is_deployed() called
    result = runner.is_deployed()

    # Then returns False
    assert result is False


def test_given_valid_topology_when_deploy_called_then_runs_deploy_command(
    runner, topology_path, mock_subprocess_run
) -> None:
    # Given valid topology
    # When deploy() called
    runner.deploy()

    # Then runs deploy command
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    assert "deploy" in call_args
    assert "-t" in call_args
    assert str(topology_path) in call_args


def test_given_deploy_fails_when_deploy_called_then_raises_deployment_error(runner, mock_subprocess_run) -> None:
    # Given deploy fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="docker not running")

    # When deploy() called
    # Then raises DeploymentError
    with pytest.raises(DeploymentError, match="Deploy failed"):
        runner.deploy()


def test_given_running_lab_when_destroy_called_then_runs_destroy_command(
    runner, topology_path, mock_subprocess_run
) -> None:
    # Given running lab
    # When destroy() called
    runner.destroy()

    # Then runs destroy command
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    assert "destroy" in call_args
    assert "-t" in call_args
    assert "--cleanup" in call_args
    assert str(topology_path) in call_args


def test_given_running_lab_when_inspect_called_then_returns_lab_name_and_nodes(runner, mock_subprocess_run) -> None:
    # Given running lab
    mock_subprocess_run.return_value.stdout = inspect_json(node_name="router1")

    # When inspect() called
    lab_name, nodes = runner.inspect()

    # Then returns lab name and nodes
    assert lab_name == "test"
    assert "router1" in nodes
    assert nodes["router1"].name == "clab-test-router1"
    assert nodes["router1"].short_name == "router1"
    assert nodes["router1"].ipv4_address == "172.20.20.2"
    assert nodes["router1"].state == "running"
    assert nodes["router1"].status == "Up 5 minutes"


def test_given_inspect_fails_when_inspect_called_then_raises_inspect_error(runner, mock_subprocess_run) -> None:
    # Given inspect fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="lab not found")

    # When inspect() called
    # Then raises InspectError
    with pytest.raises(InspectError, match="Inspect failed"):
        runner.inspect()


def test_given_empty_containers_when_inspect_called_then_raises_inspect_error(runner, mock_subprocess_run) -> None:
    # Given empty containers
    mock_subprocess_run.return_value.stdout = json.dumps({"test": []})

    # When inspect() called
    # Then raises InspectError
    with pytest.raises(InspectError, match="No containers found"):
        runner.inspect()


def test_given_missing_container_field_when_inspect_called_then_raises_inspect_error(
    runner, mock_subprocess_run
) -> None:
    # Given missing container field (missing container_id and status)
    mock_subprocess_run.return_value.stdout = json.dumps(
        {
            "test": [
                {
                    "lab_name": "test",
                    "name": "clab-test-router1",
                    "image": "alpine:latest",
                    "kind": "linux",
                    "state": "running",
                }
            ]
        }
    )

    # When inspect() called
    # Then raises InspectError
    with pytest.raises(InspectError, match="Missing expected field"):
        runner.inspect()


def test_given_inspect_returns_invalid_json_when_inspect_called_then_raises_inspect_error(
    runner, mock_subprocess_run
) -> None:
    # Given inspect returns invalid JSON
    mock_subprocess_run.return_value.stdout = "not-valid-json"

    # When inspect() called
    # Then raises InspectError
    with pytest.raises(InspectError, match="invalid JSON"):
        runner.inspect()


@pytest.mark.parametrize(
    "full_name, lab_name, expected_short_name",
    [
        ("clab-test-lab-router1", "test-lab", "router1"),
        ("clab-test-lab-leaf-1-west", "test-lab", "leaf-1-west"),
        ("clab-other-lab-router1", "test-lab", "clab-other-lab-router1"),
    ],
)
def test_given_full_name_when_short_name_extracted_then_returns_expected_short_name(
    runner,
    full_name,
    lab_name,
    expected_short_name,
) -> None:
    # Given full name

    # When _extract_short_name() called
    result = runner._extract_short_name(full_name, lab_name)

    # Then returns expected short_name
    assert result == expected_short_name


def test_given_destroy_fails_when_destroy_called_then_logs_warning_without_raising(
    runner, mock_subprocess_run, caplog
) -> None:
    # Given destroy fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="lab not found")

    # When destroy() called
    with caplog.at_level(logging.WARNING):
        runner.destroy()

    # Then logs warning without raising
    assert "Destroy failed" in caplog.text


def test_given_destroy_times_out_when_destroy_called_then_logs_warning_without_raising(
    runner, mock_subprocess_run, caplog
) -> None:
    # Given destroy times out
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=300)

    # When destroy() called
    with caplog.at_level(logging.WARNING):
        runner.destroy()

    # Then logs warning without raising
    assert "Destroy timed out" in caplog.text


def test_given_extra_container_properties_when_inspect_called_then_stored_in_properties(
    runner, mock_subprocess_run
) -> None:
    # Given extra container properties
    mock_subprocess_run.return_value.stdout = json.dumps(
        {
            "test": [
                {
                    "lab_name": "test",
                    "name": "clab-test-router1",
                    "container_id": "abc123",
                    "image": "alpine:latest",
                    "kind": "linux",
                    "state": "running",
                    "status": "Up 5 minutes",
                    "ipv4_address": "172.20.20.2/24",
                    "labels": {"app": "test"},
                    "ports": ["8080:80"],
                    "custom_field": "custom_value",
                }
            ]
        }
    )

    # When inspect() called
    _, nodes = runner.inspect()

    # Then extra properties stored in properties dict
    n = nodes["router1"]
    assert "labels" in n.properties
    assert "ports" in n.properties
    assert "custom_field" in n.properties
    assert n.properties["labels"] == {"app": "test"}


def test_given_command_when_cmd_called_then_passes_args_directly(runner, mock_subprocess_run) -> None:
    # Given command with args
    # When cmd() called
    runner.cmd("version -j")

    # Then args passed directly
    call_args = mock_subprocess_run.call_args[0][0]
    assert "version" in call_args
    assert "-j" in call_args


def test_given_parse_json_true_when_cmd_called_then_returns_parsed_json(runner, mock_subprocess_run) -> None:
    # Given parse_json True
    mock_subprocess_run.return_value.stdout = json.dumps({"test": [{"name": "node1"}]})

    # When cmd() called with parse_json=True
    result = runner.cmd("inspect -f json", parse_json=True)

    # Then returns parsed JSON
    assert isinstance(result, dict)
    assert "test" in result


def test_given_parse_json_with_invalid_json_when_cmd_called_then_raises_command_error(
    runner, mock_subprocess_run
) -> None:
    # Given parse_json with invalid JSON output
    mock_subprocess_run.return_value.stdout = "not-json"

    # When cmd() called with parse_json=True and invalid JSON
    # Then raises CommandError
    with pytest.raises(CommandError, match="invalid JSON"):
        runner.cmd("inspect", parse_json=True)


def test_given_command_fails_when_cmd_called_then_raises_command_error(runner, mock_subprocess_run) -> None:
    # Given command fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="command not found")

    # When cmd() called
    # Then raises CommandError
    with pytest.raises(CommandError, match="Command .* failed"):
        runner.cmd("invalid-command")


def test_given_successful_command_when_cmd_called_then_returns_stdout(runner, mock_subprocess_run) -> None:
    # Given successful command
    mock_subprocess_run.return_value.stdout = "output text"

    # When cmd() called
    result = runner.cmd("save")

    # Then returns stdout
    assert result == "output text"


def test_given_empty_command_when_cmd_called_then_raises_value_error(runner) -> None:
    # Given empty command
    # When cmd() called with empty string
    # Then raises ValueError
    with pytest.raises(ValueError, match="non-empty command"):
        runner.cmd("")

    with pytest.raises(ValueError, match="non-empty command"):
        runner.cmd("   ")


def test_given_empty_stdout_when_cmd_called_then_falls_back_to_stderr(runner, mock_subprocess_run) -> None:
    # Given empty stdout (containerlab writes INFO logs to stderr on some commands)
    mock_subprocess_run.return_value.stderr = "info message"

    # When cmd() called
    result = runner.cmd("save")

    # Then falls back to stderr
    assert result == "info message"


def test_given_quoted_args_when_cmd_called_then_handles_quotes_correctly(runner, mock_subprocess_run) -> None:
    # Given command with quoted arguments
    # When cmd() called with quoted args
    runner.cmd('exec --cmd "show version | as json"')

    # Then handles quotes correctly
    call_args = mock_subprocess_run.call_args[0][0]
    assert "exec" in call_args
    assert "--cmd" in call_args
    assert "show version | as json" in call_args


def test_given_timeout_setting_when_run_called_then_passes_timeout_to_subprocess(runner, mock_subprocess_run) -> None:
    # Given timeout setting (default 300 from fixture)
    # When _run() called
    runner._run(["version"])

    # Then passes timeout to subprocess
    call_kwargs = mock_subprocess_run.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] == 300


def test_given_custom_timeout_when_run_called_then_uses_custom_timeout(topology_path, mock_subprocess_run) -> None:
    # Given custom timeout
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        custom_runner = ClabRunner(topology_path, command_timeout=600)

    # When _run() called
    custom_runner._run(["version"])

    # Then uses custom timeout
    call_kwargs = mock_subprocess_run.call_args[1]
    assert call_kwargs["timeout"] == 600


def test_given_run_override_timeout_when_run_called_then_uses_override(topology_path, mock_subprocess_run) -> None:
    # Given runner with default timeout
    with patch("shutil.which", return_value="/usr/bin/containerlab"):
        custom_runner = ClabRunner(topology_path, command_timeout=600)

    # When _run() called with override
    custom_runner._run(["version"], command_timeout=7)

    # Then uses override timeout
    call_kwargs = mock_subprocess_run.call_args[1]
    assert call_kwargs["timeout"] == 7


@pytest.mark.parametrize(
    "method, args, expected_error",
    [
        ("deploy", [], DeploymentError),
        ("inspect", [], InspectError),
        ("cmd", ["version"], CommandError),
    ],
)
def test_given_operation_times_out_when_called_then_raises_appropriate_error(
    runner, mock_subprocess_run, method, args, expected_error
) -> None:
    # Given operation times out
    mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=300)

    # When method called
    # Then raises appropriate error with timeout message
    with pytest.raises(expected_error, match="timed out"):
        getattr(runner, method)(*args)


def test_given_all_nodes_running_when_wait_until_running_called_then_returns_immediately(
    runner, mock_subprocess_run
) -> None:
    # Given all nodes running
    mock_subprocess_run.return_value.stdout = inspect_json(status="Up 5 minutes")

    # When wait_until_running() called
    lab_name, nodes = runner.wait_until_running(startup_timeout=10)

    # Then returns immediately
    assert lab_name == "test"
    assert "node1" in nodes
    assert nodes["node1"].state == "running"
    assert mock_subprocess_run.call_count == 1


def test_given_nodes_not_running_when_wait_until_running_called_then_polls_until_running(
    runner, mock_subprocess_run
) -> None:
    # Given node starts as created and then becomes running
    created_output = inspect_json_with_state(state="created", status="Created")
    running_output = inspect_json_with_state(state="running", status="Up 5 seconds")
    mock_subprocess_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0, stdout=created_output, stderr=""),
        subprocess.CompletedProcess(args=[], returncode=0, stdout=running_output, stderr=""),
    ]

    # When wait_until_running() called
    with patch("time.sleep"):
        _, nodes = runner.wait_until_running(startup_timeout=30)

    # Then polls until running
    assert mock_subprocess_run.call_count == 2
    assert nodes["node1"].state == "running"


def test_given_node_exited_when_wait_until_running_called_then_raises_node_failed_error(
    runner, mock_subprocess_run
) -> None:
    # Given node enters exited state
    mock_subprocess_run.return_value.stdout = inspect_json_with_state(state="exited", status="Exited (1) 5 seconds ago")

    # When wait_until_running() called
    # Then raises NodeFailedError
    with pytest.raises(NodeFailedError, match="failed state"):
        runner.wait_until_running(startup_timeout=10)


def test_given_node_dead_when_wait_until_running_called_then_raises_node_failed_error(
    runner, mock_subprocess_run
) -> None:
    # Given node enters dead state
    mock_subprocess_run.return_value.stdout = inspect_json_with_state(state="dead", status="")

    # When wait_until_running() called
    # Then raises NodeFailedError
    with pytest.raises(NodeFailedError, match="failed state"):
        runner.wait_until_running(startup_timeout=10)


def test_given_transient_inspect_error_when_wait_until_running_called_then_retries(runner, mock_subprocess_run) -> None:
    # Given inspect fails once and then succeeds
    running_output = inspect_json_with_state(state="running", status="Up 2 seconds")
    mock_subprocess_run.side_effect = [
        subprocess.CalledProcessError(returncode=1, cmd=[], stderr="temporary failure"),
        subprocess.CompletedProcess(args=[], returncode=0, stdout=running_output, stderr=""),
    ]

    # When wait_until_running() called
    with patch("time.sleep"):
        _, nodes = runner.wait_until_running(startup_timeout=20)

    # Then retries and succeeds
    assert mock_subprocess_run.call_count == 2
    assert nodes["node1"].state == "running"


def test_given_nodes_never_running_when_wait_until_running_called_then_raises_deployment_error(
    runner, mock_subprocess_run
) -> None:
    # Given nodes stay in non-running state
    mock_subprocess_run.return_value.stdout = inspect_json_with_state(state="created", status="Created")

    # When wait_until_running() called with short timeout
    # Then raises DeploymentError
    with patch("time.sleep"):
        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.side_effect = [0, 0, 11, 11]
            with pytest.raises(DeploymentError, match="Timed out"):
                runner.wait_until_running(startup_timeout=10)


def test_given_timeout_when_wait_until_running_called_then_error_includes_node_states(
    runner, mock_subprocess_run
) -> None:
    # Given nodes never reach running
    mock_subprocess_run.return_value.stdout = inspect_json_with_state(state="created", status="Created")

    # When wait_until_running() times out
    # Then error includes node state map
    with patch("time.sleep"):
        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.side_effect = [0, 0, 11, 11]
            with pytest.raises(DeploymentError, match="node1"):
                runner.wait_until_running(startup_timeout=10)


def test_given_per_call_timeout_calculation_when_wait_until_running_called_then_uses_remaining_budget(
    runner, mock_subprocess_run
) -> None:
    # Given running node and a short remaining budget
    mock_subprocess_run.return_value.stdout = inspect_json_with_state(state="running", status="Up 1 second")

    # When called with monotonic close to deadline
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.side_effect = [0, 0]
        runner.wait_until_running(startup_timeout=5)

    # Then inspect is called using per-call timeout bounded by remaining budget
    call_kwargs = mock_subprocess_run.call_args[1]
    assert call_kwargs["timeout"] == 6


def test_given_mixed_states_when_wait_until_running_called_then_waits_for_all(runner, mock_subprocess_run) -> None:
    # Given mixed states then all running
    mixed_output = inspect_json_multi(
        [
            {"name": "node1", "state": "running", "status": "Up 5 minutes"},
            {"name": "node2", "state": "created", "status": "Created"},
        ]
    )
    all_running_output = inspect_json_multi(
        [
            {"name": "node1", "state": "running", "status": "Up 5 minutes"},
            {"name": "node2", "state": "running", "status": "Up 2 seconds"},
        ]
    )
    mock_subprocess_run.side_effect = [
        subprocess.CompletedProcess(args=[], returncode=0, stdout=mixed_output, stderr=""),
        subprocess.CompletedProcess(args=[], returncode=0, stdout=all_running_output, stderr=""),
    ]

    # When wait_until_running() called
    with patch("time.sleep"):
        _, nodes = runner.wait_until_running(startup_timeout=30)

    # Then waits for all nodes
    assert mock_subprocess_run.call_count == 2
    assert len(nodes) == 2


def test_given_inspect_always_fails_when_timeout_reached_then_error_includes_last_inspect_error(
    runner, mock_subprocess_run
) -> None:
    # Given inspect always fails
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=[], stderr="connection refused")

    # When wait_until_running() times out
    # Then error includes last inspect error
    with patch("time.sleep"):
        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.side_effect = [0, 0, 5, 11]
            with pytest.raises(DeploymentError, match="Last inspect error"):
                runner.wait_until_running(startup_timeout=10)
