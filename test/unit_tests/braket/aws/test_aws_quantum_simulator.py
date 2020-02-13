# Copyright 2019-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from unittest.mock import Mock, patch

import pytest
from braket.aws import AwsQuantumSimulator, AwsQuantumSimulatorArns
from braket.circuits import Circuit
from common_test_utils import MockDevices


@pytest.fixture
def simulator():
    def _simulator(arn):
        mock_session = Mock()
        mock_session.get_simulator_metadata.return_value = MockDevices.MOCK_QS1_SIMULATOR_1
        return AwsQuantumSimulator(arn, mock_session)

    return _simulator


@pytest.fixture
def circuit():
    return Circuit().h(0)


@pytest.fixture
def s3_destination_folder():
    return ("bucket-foo", "key-bar")


def test_simulator_refresh_metadata_success():
    mock_session = Mock()
    expected_metadata = MockDevices.MOCK_QS1_SIMULATOR_1
    mock_session.get_simulator_metadata.return_value = expected_metadata
    simulator = AwsQuantumSimulator(AwsQuantumSimulatorArns.QS1, mock_session)
    assert simulator.arn == expected_metadata.get("arn")
    assert simulator.name == expected_metadata.get("name")
    assert simulator.properties["qubitCount"] == expected_metadata.get("qubitCount")
    assert simulator.properties["supportedQuantumOperations"] == expected_metadata.get(
        "supportedQuantumOperations"
    )
    assert simulator.status == expected_metadata.get("status")
    assert simulator.status_reason is None

    # describe_simulators now returns new metadata
    expected_metadata = MockDevices.MOCK_QS1_SIMULATOR_2
    mock_session.get_simulator_metadata.return_value = expected_metadata
    simulator.refresh_metadata()
    assert simulator.arn == expected_metadata.get("arn")
    assert simulator.name == expected_metadata.get("name")
    assert simulator.properties["qubitCount"] == expected_metadata.get("qubitCount")
    assert simulator.properties["supportedQuantumOperations"] == expected_metadata.get(
        "supportedQuantumOperations"
    )
    assert simulator.status == expected_metadata.get("status")
    assert simulator.status_reason == expected_metadata.get("statusReason")


def test_simulator_refresh_metadata_error():
    mock_session = Mock()
    err_message = "nooo!"
    mock_session.get_simulator_metadata.side_effect = RuntimeError(err_message)
    with pytest.raises(RuntimeError) as excinfo:
        AwsQuantumSimulator(AwsQuantumSimulatorArns.QS1, mock_session)
    assert err_message in str(excinfo.value)


def test_equality(simulator):
    simulator_1 = simulator(AwsQuantumSimulatorArns.QS1)
    simulator_2 = simulator(AwsQuantumSimulatorArns.QS1)
    other_simulator = Mock(spec=AwsQuantumSimulator)
    other_simulator.arn.return_value = "OTHER_ARN"
    non_simulator = "HI"

    assert simulator_1 == simulator_2
    assert simulator_1 is not simulator_2
    assert simulator_1 != other_simulator
    assert simulator_1 != non_simulator


def test_repr(simulator):
    simulator = simulator(AwsQuantumSimulatorArns.QS1)
    expected = "QuantumSimulator('name': {}, 'arn': {})".format(simulator.name, simulator.arn)
    assert repr(simulator) == expected


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.create")
def test_run_with_positional_args(aws_quantum_task_mock, simulator, circuit, s3_destination_folder):
    _run_and_assert(aws_quantum_task_mock, simulator, [circuit, s3_destination_folder], {})


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.create")
def test_run_with_kwargs(aws_quantum_task_mock, simulator, circuit, s3_destination_folder):
    _run_and_assert(
        aws_quantum_task_mock,
        simulator,
        [],
        {"circuit": circuit, "s3_destination_folder": s3_destination_folder},
    )


@patch("braket.aws.aws_quantum_task.AwsQuantumTask.create")
def test_run_with_positional_args_and_kwargs(
    aws_quantum_task_mock, simulator, circuit, s3_destination_folder
):
    _run_and_assert(
        aws_quantum_task_mock, simulator, [circuit, s3_destination_folder], {"shots": 100}
    )


def _run_and_assert(aws_quantum_task_mock, simulator, run_args, run_kwargs):
    task_mock = Mock()
    aws_quantum_task_mock.return_value = task_mock

    simulator = simulator(AwsQuantumSimulatorArns.QS1)
    task = simulator.run(*run_args, **run_kwargs)
    assert task == task_mock
    aws_quantum_task_mock.assert_called_with(
        simulator._aws_session, simulator.arn, *run_args, **run_kwargs
    )