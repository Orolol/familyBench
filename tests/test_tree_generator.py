import pytest

from tree_evaluator.tree_generator import generate_tree, actual_depth


@pytest.mark.parametrize("language", ["fr", "en"])
def test_constraints_hold(language):
    tree = generate_tree(80, 4, 3, seed=7, num_root_couples=2, language=language)
    people = list(tree.values())
    assert len(people) == 80
    names = [p.first_name for p in people]
    assert len(set(names)) == len(names), "first names must be unique"
    combos = [(p.hair_color, p.eye_color, p.hat_color) for p in people]
    assert len(set(combos)) == len(combos), "appearance combination must be unique"
    for p in people:
        assert len(p.parent_ids) in (0, 2)
        for pid in p.parent_ids:
            assert p.id in tree[pid].children_ids, "parent -> child link must be bidirectional"
            assert tree[pid].generation == p.generation - 1
        for cid in p.children_ids:
            assert p.id in tree[cid].parent_ids
    # Les personnes sans parents sont soit les couples fondateurs (génération 0),
    # soit des conjoints entrés dans l'arbre par mariage (même génération que le conjoint)
    for p in people:
        if not p.parent_ids and p.generation > 0:
            assert p.children_ids, "a parentless person above generation 0 must be a spouse with children"


def test_people_are_dropped_only_when_the_tree_is_full(caplog):
    # 3 générations x 3 enfants max ne peuvent pas contenir 500 personnes
    with caplog.at_level("WARNING"):
        tree = generate_tree(500, 3, 3, seed=2, num_root_couples=1, language="en")
    assert len(tree) < 500
    assert any("could not be placed" in r.message for r in caplog.records)


def test_seed_is_reproducible():
    a = generate_tree(50, 3, 3, seed=123, num_root_couples=1, language="en")
    b = generate_tree(50, 3, 3, seed=123, num_root_couples=1, language="en")
    key = lambda t: sorted((p.first_name, p.profession, p.generation, len(p.children_ids)) for p in t.values())
    assert key(a) == key(b)


def test_depth_never_exceeds_request_and_is_reported(caplog):
    tree = generate_tree(30, 2, 3, seed=1, num_root_couples=1, language="en")
    assert actual_depth(tree) <= 2
    with caplog.at_level("WARNING"):
        tree = generate_tree(40, 10, 3, seed=1, num_root_couples=5, language="en")
    assert actual_depth(tree) < 10
    assert any("Requested depth" in r.message for r in caplog.records)


@pytest.mark.parametrize("kwargs", [
    dict(total_people=0, max_depth=3, max_children_per_person=3),
    dict(total_people=10, max_depth=0, max_children_per_person=3),
    dict(total_people=10, max_depth=3, max_children_per_person=0),
    dict(total_people=10, max_depth=3, max_children_per_person=3, num_root_couples=0),
    dict(total_people=10, max_depth=3, max_children_per_person=3, language="de"),
])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        generate_tree(seed=1, **kwargs)
