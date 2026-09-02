"""Questions sur les relations complexes (frères/sœurs, grands-parents, etc.)."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import get_siblings, get_uncles_aunts, get_cousins, get_nephews_nieces, get_half_siblings, get_step_parents, get_co_parents, format_answer


def generate_complex_relation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions sur les relations complexes."""
    questions = []
    for person in people.values():
        # Frères et soeurs
        if person.parent_ids:
            siblings = get_siblings(person, people)
            sibling_names = [s.first_name for s in siblings]
            questions.append({
                "question": get_translation("q_siblings_of", language).format(name=person.first_name),
                "answer": format_answer(sibling_names, language),
                "type": "relation_complexe"
            })

            brothers = [s.first_name for s in siblings if s.gender == 'M']
            questions.append({
                "question": get_translation("q_brothers_of", language).format(name=person.first_name),
                "answer": format_answer(brothers, language),
                "type": "relation_complexe"
            })

            sisters = [s.first_name for s in siblings if s.gender == 'F']
            questions.append({
                "question": get_translation("q_sisters_of", language).format(name=person.first_name),
                "answer": format_answer(sisters, language),
                "type": "relation_complexe"
            })

        # Grands-parents
        grandparent_names = []
        grandfathers = []
        grandmothers = []
        for pid in person.parent_ids:
            parent = people[pid]
            for gpid in parent.parent_ids:
                gp = people[gpid]
                grandparent_names.append(gp.first_name)
                if gp.gender == 'M':
                    grandfathers.append(gp.first_name)
                else:
                    grandmothers.append(gp.first_name)
        
        if grandparent_names:
            questions.append({
                "question": get_translation("q_grandparents_of", language).format(name=person.first_name),
                "answer": format_answer(grandparent_names, language),
                "type": "relation_complexe"
            })

            if grandfathers:
                questions.append({
                    "question": get_translation("q_grandfathers_of", language).format(name=person.first_name),
                    "answer": format_answer(grandfathers, language),
                    "type": "relation_complexe"
                })

            if grandmothers:
                questions.append({
                    "question": get_translation("q_grandmothers_of", language).format(name=person.first_name),
                    "answer": format_answer(grandmothers, language),
                    "type": "relation_complexe"
                })

        # Petits-enfants
        grandchildren_names = []
        grandsons = []
        granddaughters = []
        for cid in person.children_ids:
            child = people[cid]
            for gcid in child.children_ids:
                gc = people[gcid]
                grandchildren_names.append(gc.first_name)
                if gc.gender == 'M':
                    grandsons.append(gc.first_name)
                else:
                    granddaughters.append(gc.first_name)
        
        if grandchildren_names:
            questions.append({
                "question": get_translation("q_grandchildren_of", language).format(name=person.first_name),
                "answer": format_answer(grandchildren_names, language),
                "type": "relation_complexe"
            })

            if grandsons:
                questions.append({
                    "question": get_translation("q_grandsons_of", language).format(name=person.first_name),
                    "answer": format_answer(grandsons, language),
                    "type": "relation_complexe"
                })

            if granddaughters:
                questions.append({
                    "question": get_translation("q_granddaughters_of", language).format(name=person.first_name),
                    "answer": format_answer(granddaughters, language),
                    "type": "relation_complexe"
                })
        
        # Arrière-grands-parents
        great_grandparent_names = []
        great_grandfathers = []
        great_grandmothers = []
        for pid in person.parent_ids:
            parent = people[pid]
            for gpid in parent.parent_ids:
                grandparent = people[gpid]
                for ggpid in grandparent.parent_ids:
                    ggp = people[ggpid]
                    great_grandparent_names.append(ggp.first_name)
                    if ggp.gender == 'M':
                        great_grandfathers.append(ggp.first_name)
                    else:
                        great_grandmothers.append(ggp.first_name)
        
        if great_grandparent_names:
            questions.append({
                "question": get_translation("q_great_grandparents", language).format(name=person.first_name),
                "answer": format_answer(great_grandparent_names, language),
                "type": "relation_complexe"
            })

            if great_grandfathers:
                questions.append({
                    "question": get_translation("q_great_grandfathers", language).format(name=person.first_name),
                    "answer": format_answer(great_grandfathers, language),
                    "type": "relation_complexe"
                })

            if great_grandmothers:
                questions.append({
                    "question": get_translation("q_great_grandmothers", language).format(name=person.first_name),
                    "answer": format_answer(great_grandmothers, language),
                    "type": "relation_complexe"
                })
        
        # Arrière-petits-enfants
        great_grandchildren_names = []
        great_grandsons = []
        great_granddaughters = []
        for cid in person.children_ids:
            child = people[cid]
            for gcid in child.children_ids:
                grandchild = people[gcid]
                for ggcid in grandchild.children_ids:
                    ggc = people[ggcid]
                    great_grandchildren_names.append(ggc.first_name)
                    if ggc.gender == 'M':
                        great_grandsons.append(ggc.first_name)
                    else:
                        great_granddaughters.append(ggc.first_name)
        
        if great_grandchildren_names:
            questions.append({
                "question": get_translation("q_great_grandchildren", language).format(name=person.first_name),
                "answer": format_answer(great_grandchildren_names, language),
                "type": "relation_complexe"
            })

            if great_grandsons:
                questions.append({
                    "question": get_translation("q_great_grandsons", language).format(name=person.first_name),
                    "answer": format_answer(great_grandsons, language),
                    "type": "relation_complexe"
                })

            if great_granddaughters:
                questions.append({
                    "question": get_translation("q_great_granddaughters", language).format(name=person.first_name),
                    "answer": format_answer(great_granddaughters, language),
                    "type": "relation_complexe"
                })
        
        # Oncles/Tantes (frères et sœurs complets des parents)
        uncles_aunts = get_uncles_aunts(person, people)

        if uncles_aunts:
            uncle_aunt_names = [p.first_name for p in uncles_aunts]
            questions.append({
                "question": get_translation("q_uncles_aunts", language).format(name=person.first_name),
                "answer": format_answer(uncle_aunt_names, language),
                "type": "relation_complexe"
            })

            uncles = [p.first_name for p in uncles_aunts if p.gender == 'M']
            questions.append({
                "question": get_translation("q_uncles", language).format(name=person.first_name),
                "answer": format_answer(uncles, language),
                "type": "relation_complexe"
            })

            aunts = [p.first_name for p in uncles_aunts if p.gender == 'F']
            questions.append({
                "question": get_translation("q_aunts", language).format(name=person.first_name),
                "answer": format_answer(aunts, language),
                "type": "relation_complexe"
            })

        # Cousins (enfants des oncles et tantes)
        cousin_people = get_cousins(person, people)
        cousins = [c.first_name for c in cousin_people]

        if cousins:
            questions.append({
                "question": get_translation("q_cousins_all", language).format(name=person.first_name),
                "answer": format_answer(cousins, language),
                "type": "relation_complexe"
            })

            # Cousins masculins
            male_cousins = [c.first_name for c in cousin_people if c.gender == 'M']

            if male_cousins:
                questions.append({
                    "question": get_translation("q_cousins_male", language).format(name=person.first_name),
                    "answer": format_answer(male_cousins, language),
                    "type": "relation_complexe"
                })

            # Cousines féminines
            female_cousins = [c.first_name for c in cousin_people if c.gender == 'F']

            if female_cousins:
                questions.append({
                    "question": get_translation("q_cousins_female", language).format(name=person.first_name),
                    "answer": format_answer(female_cousins, language),
                    "type": "relation_complexe"
                })

        # Neveux et nièces
        nephew_people = get_nephews_nieces(person, people)
        nephews_nieces = [n.first_name for n in nephew_people]

        if nephews_nieces:
            questions.append({
                "question": get_translation("q_nephews_nieces", language).format(name=person.first_name),
                "answer": format_answer(nephews_nieces, language),
                "type": "relation_complexe"
            })

            # Neveux masculins
            nephews = [n.first_name for n in nephew_people if n.gender == 'M']

            if nephews:
                questions.append({
                    "question": get_translation("q_nephews", language).format(name=person.first_name),
                    "answer": format_answer(nephews, language),
                    "type": "relation_complexe"
                })

            # Nièces féminines
            nieces = [n.first_name for n in nephew_people if n.gender == 'F']

            if nieces:
                questions.append({
                    "question": get_translation("q_nieces", language).format(name=person.first_name),
                    "answer": format_answer(nieces, language),
                    "type": "relation_complexe"
                })

    return questions


def generate_half_family_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Demi-fratrie, beaux-parents, co-parents (secondes unions)."""
    questions: List[Dict[str, Any]] = []
    for person in people.values():
        halves = get_half_siblings(person, people)
        if halves:
            questions.append({
                "question": get_translation("q_half_siblings_of", language).format(name=person.first_name),
                "answer": format_answer([h.first_name for h in halves], language),
                "type": "demi_fratrie",
            })
            questions.append({
                "question": get_translation("q_how_many_half_siblings", language).format(name=person.first_name),
                "answer": str(len(halves)),
                "type": "demi_fratrie",
            })
            brothers = [h.first_name for h in halves if h.gender == "M"]
            sisters = [h.first_name for h in halves if h.gender == "F"]
            if brothers and sisters:
                questions.append({
                    "question": get_translation("q_half_brothers_of", language).format(name=person.first_name),
                    "answer": format_answer(brothers, language),
                    "type": "demi_fratrie",
                })
        steps = get_step_parents(person, people)
        if steps:
            questions.append({
                "question": get_translation("q_step_parents_of", language).format(name=person.first_name),
                "answer": format_answer([s.first_name for s in steps], language),
                "type": "beaux_parents",
            })
        partners = get_co_parents(person, people)
        if len(partners) >= 2:
            questions.append({
                "question": get_translation("q_co_parents_of", language).format(name=person.first_name),
                "answer": format_answer([c.first_name for c in partners], language),
                "type": "beaux_parents",
            })
    return questions
