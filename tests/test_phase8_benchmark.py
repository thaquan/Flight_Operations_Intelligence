import pytest

from src.phase8.benchmark import execution_order, require_equal, sample, summarize


def test_alternating_order_and_bounds():
    assert execution_order(3) == [("fact", "mart"), ("mart", "fact"), ("fact", "mart")]
    for invalid in (0, 2, 10, True):
        with pytest.raises(ValueError):
            execution_order(invalid)


def test_summary_uses_median_and_preserves_raw_samples():
    samples = [{"execution_ms": n} for n in (8, 100, 4)]
    assert summarize(samples) == {
        "samples": samples, "median_ms": 8, "min_ms": 4, "max_ms": 100,
    }


@pytest.mark.parametrize("samples", [[], [{"execution_ms": 0}]])
def test_invalid_samples(samples):
    with pytest.raises(ValueError):
        summarize(samples)


def test_plan_sample_uses_root_buffers_not_double_counted_children():
    result = sample({"Execution Time": 12, "Planning Time": 1, "Plan": {
        "Node Type": "Aggregate", "Shared Hit Blocks": 10, "Shared Read Blocks": 5,
        "Plans": [{"Node Type": "Seq Scan", "Shared Hit Blocks": 10}],
    }})
    assert result["shared_hit_blocks"] == 10
    assert result["shared_read_blocks"] == 5
    assert result["nodes"] == ["Aggregate", "Seq Scan"]


def test_equivalence_required():
    require_equal([(1, 2)], [(1, 2)], "test")
    with pytest.raises(ValueError, match="differ"):
        require_equal([(1, 2)], [(1, 3)], "test")
