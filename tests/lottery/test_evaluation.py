import pytest

from lrei.lottery.evaluation import paired_block_bootstrap_ci, paired_origin_block_bootstrap_ci


def test_paired_block_bootstrap_is_reproducible():
    differences = [(-1.0 if index % 7 < 3 else 0.5) for index in range(40)]
    first = paired_block_bootstrap_ci(differences, seed=123, block_size=5)
    second = paired_block_bootstrap_ci(differences, seed=123, block_size=5)
    assert first == second
    assert first[0] <= first[1]


def test_paired_block_bootstrap_constant_difference_has_zero_width_ci():
    assert paired_block_bootstrap_ci([0.25] * 20, seed=9) == (0.25, 0.25)


def test_paired_block_bootstrap_clamps_block_size_to_sample_size():
    values = [0.0, 1.0, 2.0]
    result = paired_block_bootstrap_ci(values, block_size=100, samples=100, seed=2)
    assert result == (1.0, 1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"block_size": 0},
        {"samples": 0},
        {"confidence": 0.0},
        {"confidence": 1.0},
    ],
)
def test_paired_block_bootstrap_rejects_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        paired_block_bootstrap_ci([0.0, 1.0], **kwargs)


def test_paired_block_bootstrap_rejects_empty_or_nonfinite_values():
    with pytest.raises(ValueError, match="must not be empty"):
        paired_block_bootstrap_ci([])
    with pytest.raises(ValueError, match="finite"):
        paired_block_bootstrap_ci([0.0, float("nan")])


def test_multi_origin_bootstrap_preserves_weights_and_never_bridges_gaps():
    # Every resample keeps 10 positive and 20 negative values. Sampling a
    # concatenated series would cross the gap and give a spurious interval.
    result = paired_origin_block_bootstrap_ci([[2.0] * 10, [-1.0] * 20], samples=100)
    assert result == (0.0, 0.0)


def test_multi_origin_bootstrap_is_reproducible_and_rejects_empty_origin():
    origins = [[0.0, 1.0, -1.0] * 5, [0.5, -0.5] * 10]
    assert paired_origin_block_bootstrap_ci(origins, seed=2) == paired_origin_block_bootstrap_ci(origins, seed=2)
    with pytest.raises(ValueError, match="empty"):
        paired_origin_block_bootstrap_ci([[0.0], []])
