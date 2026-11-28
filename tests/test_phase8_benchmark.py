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


def test_index_experiment_refuses_main_and_wrong_port():
    from src.phase8.index_experiment import require_target

    require_target({"POSTGRES_DB": "flight_m75_acceptance", "POSTGRES_PORT": "5543"})
    for db, port in (("flight_warehouse", "5433"), ("flight_m73_test", "5543"),
                     ("flight_m75_acceptance", "5433")):
        with pytest.raises(RuntimeError, match="isolated"):
            require_target({"POSTGRES_DB": db, "POSTGRES_PORT": port})


def test_index_names_walk_nested_plans():
    from src.phase8.index_experiment import index_names

    assert index_names({"Node Type": "Bitmap Heap Scan", "Plans": [
        {"Node Type": "BitmapAnd", "Plans": [
            {"Index Name": "month_index"}, {"Index Name": "airport_index"},
        ]},
    ]}) == ["month_index", "airport_index"]
    assert index_names({"Node Type": "Seq Scan"}) == []
