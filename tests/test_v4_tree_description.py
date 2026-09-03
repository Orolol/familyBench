"""Générateur 4.0 : secondes unions, description à sens mêlés, liens dérivés."""
import collections
import random
import re

import pytest

from tree_evaluator.tree_generator import generate_tree, actual_depth
from tree_evaluator.text_converter import convert_tree_to_text, build_description_facts
from tree_evaluator.question_generator import generate_questions
from tree_evaluator.questions.base import (
    get_siblings, get_half_siblings, get_uncles_aunts, get_cousins, get_nephews_nieces,
    get_co_parents, get_step_parents,
)


@pytest.fixture(scope="module")
def tree():
    return generate_tree(300, 7, 2, seed=11, num_root_couples=3, language="en", second_union_percentage=30)


def _partners(p, tree):
    return {pid for c in p.children_ids for pid in tree[c].parent_ids if pid != p.id}


def test_second_unions_create_half_siblings_and_keep_constraints(tree):
    multi = [p for p in tree.values() if len(_partners(p, tree)) > 1]
    assert multi, "some people must have children with two partners"
    assert all(len(_partners(p, tree)) <= 2 for p in tree.values())
    for p in tree.values():
        assert len(p.parent_ids) in (0, 2)
        for pid in p.parent_ids:
            assert p.id in tree[pid].children_ids
    names = [p.first_name for p in tree.values()]
    assert len(set(names)) == len(names)
    assert any(get_half_siblings(p, tree) for p in tree.values())
    assert any(get_step_parents(p, tree) for p in tree.values())


def test_no_second_unions_when_disabled():
    t = generate_tree(120, 5, 2, seed=3, num_root_couples=2, language="en", second_union_percentage=0)
    assert all(len(_partners(p, t)) <= 1 for p in t.values())
    assert not any(get_half_siblings(p, t) for p in t.values())


def test_relation_helpers_semantics(tree):
    for p in tree.values():
        sib = get_siblings(p, tree)
        half = get_half_siblings(p, tree)
        assert not ({s.id for s in sib} & {h.id for h in half})
        for s in sib:
            assert set(s.parent_ids) == set(p.parent_ids)
        for h in half:
            assert len(set(h.parent_ids) & set(p.parent_ids)) == 1
        for ua in get_uncles_aunts(p, tree):
            assert any(set(ua.parent_ids) == set(tree[pid].parent_ids) for pid in p.parent_ids)
        cousins = {c.id for c in get_cousins(p, tree)}
        assert cousins == {cid for ua in get_uncles_aunts(p, tree) for cid in ua.children_ids}
        assert {n.id for n in get_nephews_nieces(p, tree)} == {cid for s in sib for cid in s.children_ids}
        for sp in get_step_parents(p, tree):
            assert sp.id not in p.parent_ids
            assert any(sp.id in {cp.id for cp in get_co_parents(tree[pid], tree)} for pid in p.parent_ids)


def test_sibling_questions_exclude_half_siblings(tree):
    qs = generate_questions(tree, 300, language="en", anonymize_percentage=0, max_answer_names=0)
    by_name = {p.first_name: p for p in tree.values()}
    for q in qs:
        m = re.match(r"Who are (\w+)'s siblings\?", q["question"])
        if m:
            p = by_name[m.group(1)]
            expected = sorted(s.first_name for s in get_siblings(p, tree)) or ["None"]
            assert q["answer"].split(",") == expected
            assert not ({h.first_name for h in get_half_siblings(p, tree)} & set(q["answer"].split(",")))
    assert any(q["type"] in ("demi_fratrie", "beaux_parents") for q in qs)


def _reconstruct(facts, tree):
    """Reconstruit parent_ids depuis les faits (liens directs + liens dérivés)."""
    parents = collections.defaultdict(set)
    for f in facts:
        if f["kind"] == "link":
            parents[f["person_id"]].add(f["parent_id"])
        elif f["kind"] == "parents":
            parents[f["person_id"]] = set(tree[f["person_id"]].parent_ids)  # phrase explicite
    for f in facts:
        if f["kind"] == "derived":
            assert f["anchor_id"] in parents and len(parents[f["anchor_id"]]) == 2, "anchor must be explicit"
            parents[f["person_id"]] = set(parents[f["anchor_id"]])
    return parents


def test_mixed_description_states_each_link_once_and_is_reconstructible(tree):
    rng = random.Random(1)
    facts = build_description_facts(tree, "en", "mixed", derived_links_percentage=30, rng=rng)
    links = [f for f in facts if f["kind"] == "link"]
    derived = [f for f in facts if f["kind"] == "derived"]
    assert derived, "some people must be described through a sibling"
    assert {f["direction"] for f in links} == {"parent", "child"}
    seen = collections.Counter((f["person_id"], f["parent_id"]) for f in links)
    assert all(v == 1 for v in seen.values())
    derived_ids = {f["person_id"] for f in derived}
    assert not any(f["person_id"] in derived_ids for f in links), "a derived person has no direct link"
    assert not any(f["anchor_id"] in derived_ids for f in derived), "an anchor is never derived"
    for f in derived:
        assert set(tree[f["anchor_id"]].parent_ids) == set(tree[f["person_id"]].parent_ids)
    parents = _reconstruct(facts, tree)
    for p in tree.values():
        assert parents.get(p.id, set()) == set(p.parent_ids), p.first_name


def test_description_is_seeded_and_has_conventions(tree):
    random.seed(1); a = convert_tree_to_text(tree, shuffle=True, language="en", seed=5, derived_links_percentage=30)
    random.seed(2); b = convert_tree_to_text(tree, shuffle=True, language="en", seed=5, derived_links_percentage=30)
    assert a == b
    assert a.startswith("Conventions:")
    assert " a orange " not in a and " a auburn " not in a
    assert " is the sister of " in a or " is the brother of " in a
    fr = convert_tree_to_text(tree, shuffle=True, language="fr", seed=5, derived_links_percentage=30)
    assert fr.startswith("Conventions :") and (" est la sœur de " in fr or " est le frère de " in fr)


def test_parents_mode_still_available(tree):
    d = convert_tree_to_text(tree, language="en", relations="parents", conventions=False)
    assert " is the child of " in d and " is the father of " not in d


def test_default_two_children_gives_deeper_trees():
    shallow = generate_tree(400, 12, 3, seed=43, num_root_couples=4, language="en", second_union_percentage=0)
    deep = generate_tree(400, 12, 2, seed=43, num_root_couples=4, language="en", second_union_percentage=0)
    assert actual_depth(deep) > actual_depth(shallow)
