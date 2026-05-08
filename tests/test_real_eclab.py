"""Integration tests that run against a live EC-Lab.exe.

Run with `pytest --real-eclab`.

You must have a copy of EC-lab open, and have some instrument available.

Add a 'virtual potentiostat' in EC-lab if you have no hardware available.

Tests should not affect any experiments, but do not run if you have real experiments running.

"""

import pytest

import aurora_biologic.biologic as bio
from aurora_biologic.dicts import (
    status_codes,
    status_nested_codes,
)


@pytest.mark.real_eclab
def test_status_returns_dict(real_bio: bio.BiologicAPI) -> None:
    """Test status works."""
    res = real_bio.get_status(show_offline=True)
    assert isinstance(res, dict)

    # Check the first the first key
    key = next(k for k in res)
    pipeline1 = res[key]
    assert isinstance(key, str)
    assert isinstance(pipeline1, dict)
    assert set(pipeline1.keys()) == set(status_codes.values())
    assert pipeline1["Status"] in set(status_nested_codes[0].values())


@pytest.mark.real_eclab
def test_get_pipelines(real_bio: bio.BiologicAPI) -> None:
    """Check get_pipelines behaves as expected."""
    res = real_bio.get_pipelines(show_offline=True)
    assert isinstance(res, dict)

    # Check the first the first key
    key = next(k for k in res)
    pipeline1 = res[key]
    assert isinstance(key, str)
    assert isinstance(pipeline1, dict)
    assert set(pipeline1.keys()) == {
        "channel_index",
        "channel_serial_number",
        "device_index",
        "device_name",
        "device_serial_number",
        "is_online",
    }


@pytest.mark.real_eclab
def test_switch_channel(real_bio: bio.BiologicAPI) -> None:
    """Check that switching between channels works."""
    res = real_bio.get_pipelines(show_offline=True)
    pipeline_name_1 = next(k for k in res)
    pipeline_name_2 = next(k for k in res)

    # Should not raise runtimeerrors from OLE-COM
    dev_idx, channel_idx = real_bio._get_pipeline_indices(pipeline_name_1)
    real_bio._olecom_select_channel(dev_idx, channel_idx)

    dev_idx, channel_idx = real_bio._get_pipeline_indices(pipeline_name_2)
    real_bio._olecom_select_channel(dev_idx, channel_idx)

    # Trying to switch to a device that doesn't exist raises an error
    with pytest.raises(RuntimeError):
        real_bio._olecom_select_channel(8589869056, 137438691328)
