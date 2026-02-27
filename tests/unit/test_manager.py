"""Unit tests for ClabManager."""

from unittest.mock import patch

import pytest

from pytest_clab.exceptions import DeploymentError, NodeFailedError
from pytest_clab.manager import ClabManager
from pytest_clab.topology import ClabTopology
from tests.conftest import node


def test_given_lab_not_deployed_when_create_called_then_deploy_is_called(tmp_path, mock_runner) -> None:
    # Given lab not deployed
    mock_runner.is_deployed.return_value = False
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file)

    # Then deploy() is called
    mock_runner.deploy.assert_called_once()


def test_given_lab_already_deployed_when_create_called_then_deploy_is_skipped(tmp_path, mock_runner) -> None:
    # Given lab already deployed
    mock_runner.is_deployed.return_value = True
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file)

    # Then deploy() is not called
    mock_runner.deploy.assert_not_called()


def test_given_valid_topology_when_create_called_then_returns_clabtopology(tmp_path, mock_runner) -> None:
    # Given valid topology
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        topology = manager.create(topology_file)

    # Then returns ClabTopology
    assert isinstance(topology, ClabTopology)
    assert topology.name == "my-lab"
    assert "leaf1" in topology.nodes
    assert topology.nodes["leaf1"].kind == "linux"


def test_given_custom_startup_timeout_when_create_called_then_wait_timeout_forwarded(tmp_path, mock_runner) -> None:
    # Given custom startup timeout
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file, startup_timeout=45)

    # Then startup timeout forwarded to runner
    mock_runner.wait_until_running.assert_called_once_with(startup_timeout=45)


def test_given_custom_command_timeout_when_create_called_then_runner_uses_it(tmp_path, mock_runner) -> None:
    # Given custom command timeout
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner) as mock_runner_cls:
        manager = ClabManager()
        manager.create(topology_file, command_timeout=123)

    # Then constructor called with command_timeout
    mock_runner_cls.assert_called_once_with(topology_file.resolve(), sudo=False, command_timeout=123)


def test_given_keep_running_true_when_cleanup_called_then_lab_not_destroyed(tmp_path, mock_runner) -> None:
    # Given keep_running True
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file, keep_running=True)

    # When cleanup() called
    manager.cleanup()

    # Then destroy() is not called
    mock_runner.destroy.assert_not_called()


def test_given_keep_running_false_when_cleanup_called_then_lab_destroyed(tmp_path, mock_runner) -> None:
    # Given keep_running False
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file)

    # When cleanup() called
    manager.cleanup()

    # Then destroy() is called
    mock_runner.destroy.assert_called_once()


def test_given_deployment_fails_when_create_called_then_error_propagates(tmp_path, mock_runner) -> None:
    # Given deployment fails
    mock_runner.is_deployed.return_value = False
    mock_runner.deploy.side_effect = DeploymentError("Docker not running")
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    # Then DeploymentError propagates and runner is tracked for cleanup
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        with pytest.raises(DeploymentError, match="Docker not running"):
            manager.create(topology_file)

    manager.cleanup()
    mock_runner.destroy.assert_called_once()


def test_given_existing_lab_when_wait_fails_then_runner_is_untracked(tmp_path, mock_runner) -> None:
    # Given lab already deployed but wait_until_running fails
    mock_runner.is_deployed.return_value = True
    mock_runner.wait_until_running.side_effect = DeploymentError("Timed out")
    topology_file = tmp_path / "test.clab.yml"

    # When create() called on existing lab
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        with pytest.raises(DeploymentError, match="Timed out"):
            manager.create(topology_file)

    # Then runner is not tracked (we didn't deploy it, so we don't destroy it)
    manager.cleanup()
    mock_runner.destroy.assert_not_called()


def test_given_destroy_raises_unexpected_exception_when_cleanup_called_then_remaining_labs_still_cleaned(
    tmp_path, mock_runner
) -> None:
    # Given two labs, first destroy raises unexpected OSError
    mock_runner.is_deployed.return_value = True
    mock_runner.wait_until_running.return_value = ("my-lab", {"leaf1": node()})
    topology_file = tmp_path / "test.clab.yml"

    from unittest.mock import MagicMock

    failing_runner = MagicMock()
    failing_runner.destroy.side_effect = OSError("unexpected disk error")
    failing_runner._topology_path = topology_file

    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        manager.create(topology_file)

    # Manually inject a failing runner before the working one
    manager._labs.insert(0, (failing_runner, False))

    # When cleanup() called
    manager.cleanup()

    # Then both destroy() calls were attempted
    failing_runner.destroy.assert_called_once()
    mock_runner.destroy.assert_called_once()


def test_given_wait_fails_after_deploy_when_cleanup_called_then_runner_still_destroyed(tmp_path, mock_runner) -> None:
    # Given deploy succeeds but wait_until_running raises
    mock_runner.is_deployed.return_value = False
    mock_runner.wait_until_running.side_effect = DeploymentError("Timed out")
    topology_file = tmp_path / "test.clab.yml"

    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        with pytest.raises(DeploymentError):
            manager.create(topology_file)

    # When cleanup() called
    manager.cleanup()

    # Then runner is still destroyed (was tracked before wait failed)
    mock_runner.destroy.assert_called_once()


def test_given_keep_running_true_when_wait_fails_then_cleanup_still_destroys(tmp_path, mock_runner) -> None:
    # Given keep_running=True but wait_until_running raises
    mock_runner.is_deployed.return_value = False
    mock_runner.wait_until_running.side_effect = DeploymentError("Timed out")
    topology_file = tmp_path / "test.clab.yml"

    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        with pytest.raises(DeploymentError):
            manager.create(topology_file, keep_running=True)

    # When cleanup() called
    manager.cleanup()

    # Then runner is destroyed despite keep_running (failed labs are always cleaned up)
    mock_runner.destroy.assert_called_once()


def test_given_node_fails_when_create_called_then_node_failed_error_propagates(tmp_path, mock_runner) -> None:
    # Given node enters failed state
    mock_runner.is_deployed.return_value = True
    mock_runner.wait_until_running.side_effect = NodeFailedError(
        "Nodes entered failed state during startup: {'router1': 'exited'}"
    )
    topology_file = tmp_path / "test.clab.yml"

    # When create() called
    # Then NodeFailedError propagates
    with patch("pytest_clab.manager.ClabRunner", return_value=mock_runner):
        manager = ClabManager()
        with pytest.raises(NodeFailedError, match="failed state"):
            manager.create(topology_file)
