from tree_evaluator.versioning import benchmark_fingerprint, data_files_hash


def test_fingerprint_is_stable_and_sensitive():
    p = {"people": 10, "depth": 2, "questions": 5, "seed": 1, "language": "en"}
    assert benchmark_fingerprint(p) == benchmark_fingerprint(dict(p))
    assert benchmark_fingerprint(p) != benchmark_fingerprint({**p, "seed": 2})
    assert benchmark_fingerprint(p) != benchmark_fingerprint({**p, "language": "fr"})
    assert len(data_files_hash("en")) == 12
