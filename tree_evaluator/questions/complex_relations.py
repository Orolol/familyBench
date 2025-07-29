"""Questions sur les relations complexes (frères/sœurs, grands-parents, etc.)."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer


def generate_complex_relation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions sur les relations complexes."""
    questions = []
    for person in people.values():
        # Frères et soeurs
        if person.parent_ids:
            siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
            sibling_names = [s.first_name for s in siblings]
            questions.append({
                "question": get_translation("q_siblings_of", language).format(name=person.first_name),
                "answer": format_answer(list(set(sibling_names)), language),
                "type": "relation_complexe"
            })
            
            brothers = [s.first_name for s in siblings if s.gender == 'M']
            questions.append({
                "question": get_translation("q_brothers_of", language).format(name=person.first_name),
                "answer": format_answer(list(set(brothers)), language),
                "type": "relation_complexe"
            })

            sisters = [s.first_name for s in siblings if s.gender == 'F']
            questions.append({
                "question": get_translation("q_sisters_of", language).format(name=person.first_name),
                "answer": format_answer(list(set(sisters)), language),
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
                "answer": format_answer(list(set(grandparent_names)), language),
                "type": "relation_complexe"
            })
            
            if grandfathers:
                questions.append({
                    "question": get_translation("q_grandfathers_of", language).format(name=person.first_name),
                    "answer": format_answer(list(set(grandfathers)), language),
                    "type": "relation_complexe"
                })
            
            if grandmothers:
                questions.append({
                    "question": get_translation("q_grandmothers_of", language).format(name=person.first_name),
                    "answer": format_answer(list(set(grandmothers)), language),
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
                "answer": format_answer(list(set(grandchildren_names)), language),
                "type": "relation_complexe"
            })
            
            if grandsons:
                questions.append({
                    "question": get_translation("q_grandsons_of", language).format(name=person.first_name),
                    "answer": format_answer(list(set(grandsons)), language),
                    "type": "relation_complexe"
                })
            
            if granddaughters:
                questions.append({
                    "question": get_translation("q_granddaughters_of", language).format(name=person.first_name),
                    "answer": format_answer(list(set(granddaughters)), language),
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
                "answer": format_answer(list(set(great_grandparent_names)), language),
                "type": "relation_complexe"
            })
            
            if great_grandfathers:
                questions.append({
                    "question": get_translation("q_great_grandfathers", language).format(name=person.first_name),
                    "answer": format_answer(list(set(great_grandfathers)), language),
                    "type": "relation_complexe"
                })
            
            if great_grandmothers:
                questions.append({
                    "question": get_translation("q_great_grandmothers", language).format(name=person.first_name),
                    "answer": format_answer(list(set(great_grandmothers)), language),
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
                "answer": format_answer(list(set(great_grandchildren_names)), language),
                "type": "relation_complexe"
            })
            
            if great_grandsons:
                questions.append({
                    "question": get_translation("q_great_grandsons", language).format(name=person.first_name),
                    "answer": format_answer(list(set(great_grandsons)), language),
                    "type": "relation_complexe"
                })
            
            if great_granddaughters:
                questions.append({
                    "question": get_translation("q_great_granddaughters", language).format(name=person.first_name),
                    "answer": format_answer(list(set(great_granddaughters)), language),
                    "type": "relation_complexe"
                })
        
        # Oncles/Tantes
        uncles_aunts = []
        for pid in person.parent_ids:
            parent = people[pid]
            if parent.parent_ids:
                parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                uncles_aunts.extend(parent_siblings)
        
        if uncles_aunts:
            uncle_aunt_names = [p.first_name for p in uncles_aunts]
            questions.append({
                "question": get_translation("q_uncles_aunts", language).format(name=person.first_name),
                "answer": format_answer(list(set(uncle_aunt_names)), language),
                "type": "relation_complexe"
            })

            uncles = [p.first_name for p in uncles_aunts if p.gender == 'M']
            questions.append({
                "question": get_translation("q_uncles", language).format(name=person.first_name),
                "answer": format_answer(list(set(uncles)), language),
                "type": "relation_complexe"
            })

            aunts = [p.first_name for p in uncles_aunts if p.gender == 'F']
            questions.append({
                "question": get_translation("q_aunts", language).format(name=person.first_name),
                "answer": format_answer(list(set(aunts)), language),
                "type": "relation_complexe"
            })

        # Cousins
        cousins = []
        for pid in person.parent_ids:
            parent = people[pid]
            if parent.parent_ids:
                # Frères et sœurs du parent
                parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                # Enfants des frères et sœurs du parent (= cousins)
                for sibling in parent_siblings:
                    cousins.extend([people[cid].first_name for cid in sibling.children_ids])
        
        if cousins:
            questions.append({
                "question": get_translation("q_cousins_all", language).format(name=person.first_name),
                "answer": format_answer(list(set(cousins)), language),
                "type": "relation_complexe"
            })

            # Cousins masculins
            male_cousins = []
            for pid in person.parent_ids:
                parent = people[pid]
                if parent.parent_ids:
                    parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                    for sibling in parent_siblings:
                        male_cousins.extend([people[cid].first_name for cid in sibling.children_ids if people[cid].gender == 'M'])
            
            if male_cousins:
                questions.append({
                    "question": get_translation("q_cousins_male", language).format(name=person.first_name),
                    "answer": format_answer(list(set(male_cousins)), language),
                    "type": "relation_complexe"
                })

            # Cousines féminines
            female_cousins = []
            for pid in person.parent_ids:
                parent = people[pid]
                if parent.parent_ids:
                    parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                    for sibling in parent_siblings:
                        female_cousins.extend([people[cid].first_name for cid in sibling.children_ids if people[cid].gender == 'F'])
            
            if female_cousins:
                questions.append({
                    "question": get_translation("q_cousins_female", language).format(name=person.first_name),
                    "answer": format_answer(list(set(female_cousins)), language),
                    "type": "relation_complexe"
                })

        # Neveux et nièces
        nephews_nieces = []
        if person.parent_ids:
            # Frères et sœurs de la personne
            siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
            # Enfants des frères et sœurs
            for sibling in siblings:
                nephews_nieces.extend([people[cid].first_name for cid in sibling.children_ids])
        
        if nephews_nieces:
            questions.append({
                "question": get_translation("q_nephews_nieces", language).format(name=person.first_name),
                "answer": format_answer(list(set(nephews_nieces)), language),
                "type": "relation_complexe"
            })

            # Neveux masculins
            nephews = []
            if person.parent_ids:
                siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
                for sibling in siblings:
                    nephews.extend([people[cid].first_name for cid in sibling.children_ids if people[cid].gender == 'M'])
            
            if nephews:
                questions.append({
                    "question": get_translation("q_nephews", language).format(name=person.first_name),
                    "answer": format_answer(list(set(nephews)), language),
                    "type": "relation_complexe"
                })

            # Nièces féminines
            nieces = []
            if person.parent_ids:
                siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
                for sibling in siblings:
                    nieces.extend([people[cid].first_name for cid in sibling.children_ids if people[cid].gender == 'F'])
            
            if nieces:
                questions.append({
                    "question": get_translation("q_nieces", language).format(name=person.first_name),
                    "answer": format_answer(list(set(nieces)), language),
                    "type": "relation_complexe"
                })

    return questions