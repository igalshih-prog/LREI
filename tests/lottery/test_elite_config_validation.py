import pytest

from lrei.lottery.elite import EliteProConfig


def test_elite_preserves_base_config_validation():
    with pytest.raises(ValueError, match="affinity_prior_strength"):
        EliteProConfig(affinity_prior_strength=-1)

    with pytest.raises(ValueError, match="ewma_half_life"):
        EliteProConfig(ewma_half_life=0)


def test_elite_requires_positive_ensemble_weight():
    with pytest.raises(ValueError, match="positive total"):
        EliteProConfig(rank_weight=0, raw_weight=0, ewma_weight=0)

    with pytest.raises(ValueError, match="non-negative"):
        EliteProConfig(rank_weight=-0.1)
