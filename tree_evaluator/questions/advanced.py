"""Questions avancées (composées, multi-hop, conditionnelles, etc.)."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer, get_common_attributes, get_father, get_mother


def generate_compound_relation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions composées plus complexes."""
    questions = []
    
    for person in people.values():
        # Questions combinant relations et attributs
        
        # Enfants avec un attribut spécifique
        if person.children_ids:
            children_with_attr = {}
            for attr in ['hair_color', 'eye_color', 'profession']:
                for cid in person.children_ids:
                    child = people[cid]
                    attr_value = getattr(child, attr)
                    if attr not in children_with_attr:
                        children_with_attr[attr] = {}
                    if attr_value not in children_with_attr[attr]:
                        children_with_attr[attr][attr_value] = []
                    children_with_attr[attr][attr_value].append(child.first_name)
            
            # Questions sur les enfants avec attributs
            for hair_color, names in children_with_attr.get('hair_color', {}).items():
                if len(names) > 0:
                    questions.append({
                        "question": get_translation("q_children_with_hair", language).format(name=person.first_name, color=hair_color),
                        "answer": format_answer(names, language),
                        "type": "relation_attribut_composee"
                    })
            
            # Pour les professions, n'utiliser que les professions communes
            common_professions = get_common_attributes(people, 'profession', min_count=3)
            for profession, names in children_with_attr.get('profession', {}).items():
                if len(names) > 0 and profession in common_professions:
                    questions.append({
                        "question": get_translation("q_children_with_profession", language).format(name=person.first_name, profession=profession),
                        "answer": format_answer(names, language),
                        "type": "relation_attribut_composee"
                    })
        
        # Frères/sœurs avec attributs
        if person.parent_ids:
            siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
            
            # Frères/sœurs par profession (seulement les professions communes)
            common_professions = get_common_attributes(people, 'profession', min_count=3)
            sibling_professions = {}
            for sibling in siblings:
                if sibling.profession not in sibling_professions:
                    sibling_professions[sibling.profession] = []
                sibling_professions[sibling.profession].append(sibling.first_name)
            
            for profession, names in sibling_professions.items():
                if len(names) > 0 and profession in common_professions:
                    questions.append({
                        "question": get_translation("q_siblings_with_profession", language).format(name=person.first_name, profession=profession),
                        "answer": format_answer(list(set(names)), language),
                        "type": "relation_attribut_composee"
                    })
            
            # Ajouter des questions sur les frères/sœurs avec combinaisons d'attributs
            if len(siblings) > 1:
                for sibling in siblings:
                    # Frères/sœurs avec même couleur de cheveux ET yeux
                    same_appearance = [s.first_name for s in siblings 
                                     if s.hair_color == sibling.hair_color and 
                                        s.eye_color == sibling.eye_color and 
                                        s.id != sibling.id]
                    if same_appearance:
                        questions.append({
                            "question": f"Quels frères ou sœurs de {person.first_name} ont les cheveux {sibling.hair_color} et les yeux {sibling.eye_color} ?",
                            "answer": format_answer(same_appearance, language),
                            "type": "relation_attribut_composee"
                        })
                        break  # Une seule question de ce type
        
        # Questions sur chaînes de relations
        
        # Enfants des frères/sœurs (neveux/nièces) avec attributs
        if person.parent_ids:
            siblings = [people[cid] for pid in person.parent_ids for cid in people[pid].children_ids if cid != person.id]
            nephews_by_hair = {}
            for sibling in siblings:
                for child_id in sibling.children_ids:
                    child = people[child_id]
                    if child.hair_color not in nephews_by_hair:
                        nephews_by_hair[child.hair_color] = []
                    nephews_by_hair[child.hair_color].append(child.first_name)
            
            for hair_color, names in nephews_by_hair.items():
                if len(names) > 0:
                    questions.append({
                        "question": get_translation("q_nephews_nieces_with_hair", language).format(name=person.first_name, color=hair_color),
                        "answer": format_answer(list(set(names)), language),
                        "type": "relation_attribut_composee"
                    })
        
        # Parents des cousins (oncles/tantes)
        cousins = []
        for pid in person.parent_ids:
            parent = people[pid]
            if parent.parent_ids:
                parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                for sibling in parent_siblings:
                    cousins.extend([(people[cid], sibling) for cid in sibling.children_ids])
        
        if cousins:
            # Oncles/tantes par attributs physiques plutôt que professions
            uncle_aunt_hair = {}
            for cousin, parent in cousins:
                if parent.hair_color not in uncle_aunt_hair:
                    uncle_aunt_hair[parent.hair_color] = []
                uncle_aunt_hair[parent.hair_color].append(parent.first_name)
            
            for hair_color, names in uncle_aunt_hair.items():
                unique_names = list(set(names))
                if len(unique_names) > 1:  # Au moins 2 pour éviter les cas uniques
                    questions.append({
                        "question": f"Quels oncles ou tantes de {person.first_name} ont les cheveux {hair_color} ?",
                        "answer": format_answer(unique_names, language),
                        "type": "relation_attribut_composee"
                    })
        
        # Grands-parents avec attributs spécifiques
        grandparents = []
        for pid in person.parent_ids:
            parent = people[pid]
            for gpid in parent.parent_ids:
                grandparents.append(people[gpid])
        
        if grandparents:
            gp_by_hair = {}
            for gp in grandparents:
                if gp.hair_color not in gp_by_hair:
                    gp_by_hair[gp.hair_color] = []
                gp_by_hair[gp.hair_color].append(gp.first_name)
            
            for hair_color, names in gp_by_hair.items():
                if len(names) > 0:
                    questions.append({
                        "question": get_translation("q_grandparents_with_hair", language).format(name=person.first_name, color=hair_color),
                        "answer": format_answer(list(set(names)), language),
                        "type": "relation_attribut_composee"
                    })
    
    # Questions de comptage complexes
    for person in people.values():
        # Nombre de petits-enfants avec un attribut
        if person.children_ids:
            grandchildren_by_gender = {'M': [], 'F': []}
            for cid in person.children_ids:
                child = people[cid]
                for gcid in child.children_ids:
                    gc = people[gcid]
                    grandchildren_by_gender[gc.gender].append(gc.first_name)
            
            if grandchildren_by_gender['M']:
                questions.append({
                    "question": get_translation("q_how_many_grandsons", language).format(name=person.first_name),
                    "answer": str(len(grandchildren_by_gender['M'])),
                    "type": "comptage_complexe"
                })
            
            if grandchildren_by_gender['F']:
                questions.append({
                    "question": get_translation("q_how_many_granddaughters", language).format(name=person.first_name),
                    "answer": str(len(grandchildren_by_gender['F'])),
                    "type": "comptage_complexe"
                })
        
        # Nombre de cousins
        cousins = []
        for pid in person.parent_ids:
            parent = people[pid]
            if parent.parent_ids:
                parent_siblings = [people[cid] for gpid in parent.parent_ids for cid in people[gpid].children_ids if cid != pid]
                for sibling in parent_siblings:
                    cousins.extend([people[cid].first_name for cid in sibling.children_ids])
        
        if cousins:
            questions.append({
                "question": get_translation("q_how_many_cousins", language).format(name=person.first_name),
                "answer": str(len(set(cousins))),
                "type": "comptage_complexe"
            })
    
    # Questions de recherche inversée complexe
    for person in people.values():
        # Qui sont les personnes dont les parents ont une certaine profession ?
        if person.parent_ids and len(person.parent_ids) == 2:
            parents = [people[pid] for pid in person.parent_ids]
            parent_professions = [p.profession for p in parents]
            
            # Chercher d'autres personnes avec au moins un parent de même profession
            similar_people = []
            for other in people.values():
                if other.id != person.id and other.parent_ids:
                    other_parent_professions = [people[pid].profession for pid in other.parent_ids]
                    if any(prof in parent_professions for prof in other_parent_professions):
                        similar_people.append(other.first_name)
            
            # Remplacer par des questions sur les attributs physiques des parents
            if person.parent_ids:
                parent_hair_colors = [people[pid].hair_color for pid in person.parent_ids]
                for color in parent_hair_colors:
                    matching = []
                    for other in people.values():
                        if other.parent_ids:
                            if any(people[pid].hair_color == color for pid in other.parent_ids):
                                matching.append(other.first_name)
                    
                    if len(matching) > 2 and len(matching) < 10:  # Au moins 3 personnes
                        questions.append({
                            "question": f"Qui a au moins un parent aux cheveux {color} ?",
                            "answer": format_answer(list(set(matching)), language),
                            "type": "recherche_inversee_complexe"
                        })
                        break  # Une seule question de ce type
    
    return questions


def generate_multihop_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions de raisonnement en chaîne (multi-hop)."""
    questions = []
    
    for person in people.values():
        # 1. Enfants des frères et sœurs des grands-parents
        great_uncles_children = []
        for pid in person.parent_ids:
            parent = people[pid]
            for gpid in parent.parent_ids:
                grandparent = people[gpid]
                # Frères et sœurs du grand-parent
                for ggpid in grandparent.parent_ids:
                    for sibling_id in people[ggpid].children_ids:
                        if sibling_id != gpid:  # Pas le grand-parent lui-même
                            sibling = people[sibling_id]
                            great_uncles_children.extend([people[cid].first_name for cid in sibling.children_ids])
        
        if great_uncles_children:
            questions.append({
                "question": get_translation("q_children_of_siblings_of_grandparents", language).format(name=person.first_name),
                "answer": format_answer(list(set(great_uncles_children)), language),
                "type": "multihop"
            })
        
        # 2. Couleurs de cheveux des beaux-parents des enfants
        in_laws_hair = []
        for cid in person.children_ids:
            child = people[cid]
            # Si l'enfant a des enfants, trouver l'autre parent
            if child.children_ids:
                for gcid in child.children_ids:
                    grandchild = people[gcid]
                    # Trouver l'autre parent du petit-enfant
                    for other_parent_id in grandchild.parent_ids:
                        if other_parent_id != cid:
                            in_law = people[other_parent_id]
                            in_laws_hair.append(in_law.hair_color)
        
        if in_laws_hair and len(set(in_laws_hair)) > 1:  # Au moins 2 couleurs différentes
            questions.append({
                "question": f"Quelles sont les couleurs de cheveux des beaux-parents des enfants de {person.first_name} ?",
                "answer": format_answer(list(set(in_laws_hair)), language),
                "type": "multihop"
            })
        
        # 3. Qui a la même couleur de cheveux que la mère du père
        father = get_father(person, people)
        if father:
            grandmother = get_mother(father, people)
            if grandmother:
                same_hair = [p.first_name for p in people.values() 
                           if p.hair_color == grandmother.hair_color and p.id != grandmother.id]
                if same_hair:
                    questions.append({
                        "question": get_translation("q_same_hair_as_mothers_father", language).format(name=person.first_name),
                        "answer": format_answer(same_hair, language),
                        "type": "multihop"
                    })
        
        # 4. Petits-enfants des frères et sœurs
        if person.parent_ids:
            siblings_grandchildren = []
            siblings = [people[cid] for pid in person.parent_ids 
                       for cid in people[pid].children_ids if cid != person.id]
            for sibling in siblings:
                for cid in sibling.children_ids:
                    child = people[cid]
                    siblings_grandchildren.extend([people[gcid].first_name for gcid in child.children_ids])
            
            if siblings_grandchildren:
                questions.append({
                    "question": get_translation("q_grandchildren_of_siblings", language).format(name=person.first_name),
                    "answer": format_answer(list(set(siblings_grandchildren)), language),
                    "type": "multihop"
                })
    
    return questions


def generate_conditional_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions avec logique conditionnelle."""
    questions = []
    
    for person in people.values():
        # 1. Si a des frères, qui sont leurs filles
        if person.parent_ids:
            brothers = []
            for pid in person.parent_ids:
                for sibling_id in people[pid].children_ids:
                    if sibling_id != person.id and people[sibling_id].gender == 'M':
                        brothers.append(people[sibling_id])
            
            if brothers:
                daughters = []
                for brother in brothers:
                    daughters.extend([people[cid].first_name for cid in brother.children_ids 
                                    if people[cid].gender == 'F'])
                if daughters:
                    questions.append({
                        "question": get_translation("q_if_has_brothers_their_daughters", language).format(name=person.first_name),
                        "answer": format_answer(daughters, language),
                        "type": "conditional"
                    })
        
        # 2. Enfants avec enfants dans même profession
        if person.children_ids and person.profession:
            matching_children = []
            for cid in person.children_ids:
                child = people[cid]
                if child.children_ids:
                    # Vérifier si au moins un petit-enfant a la même profession
                    for gcid in child.children_ids:
                        if people[gcid].profession == person.profession:
                            matching_children.append(child.first_name)
                            break
            
            if matching_children:
                questions.append({
                    "question": get_translation("q_children_with_children_same_profession", language).format(name=person.first_name),
                    "answer": format_answer(matching_children, language),
                    "type": "conditional"
                })
        
        # 3. Qui a plus d'enfants
        if person.parent_ids:
            siblings = [people[cid] for pid in person.parent_ids 
                       for cid in people[pid].children_ids if cid != person.id]
            
            if siblings:
                person_count = len(person.children_ids)
                more_children = []
                for sibling in siblings:
                    if len(sibling.children_ids) > person_count:
                        more_children.append(sibling.first_name)
                
                answer = format_answer(more_children, language) if more_children else person.first_name
                questions.append({
                    "question": get_translation("q_who_has_more_children", language).format(name=person.first_name),
                    "answer": answer,
                    "type": "conditional"
                })
    
    return questions


def generate_negation_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions d'exclusion et de négation."""
    questions = []
    
    # 1. Qui n'a PAS d'enfants avec une certaine couleur d'yeux (choisir la plus commune)
    # D'abord trouver les couleurs d'yeux présentes
    eye_colors = {}
    for person in people.values():
        if person.eye_color not in eye_colors:
            eye_colors[person.eye_color] = 0
        eye_colors[person.eye_color] += 1
    
    # Choisir une couleur présente mais pas trop rare
    if eye_colors:
        sorted_colors = sorted(eye_colors.items(), key=lambda x: x[1], reverse=True)
        # Prendre la 2e ou 3e couleur la plus commune si possible
        target_color = sorted_colors[min(1, len(sorted_colors)-1)][0]
        
        parents_no_target_eyes = []
        for person in people.values():
            if person.children_ids:
                has_target_child = any(people[cid].eye_color == target_color 
                                     for cid in person.children_ids)
                if not has_target_child:
                    parents_no_target_eyes.append(person.first_name)
        
        if parents_no_target_eyes:  # Même s'il n'y a qu'une personne
            questions.append({
                "question": f"Qui dans la famille n'a PAS d'enfants aux yeux {target_color} ?",
                "answer": format_answer(parents_no_target_eyes, language),
                "type": "negation"
            })
    
    # 2. Qui n'a pas de frères et sœurs
    people_no_siblings = []
    for person in people.values():
        if person.parent_ids:
            siblings_count = sum(1 for pid in person.parent_ids 
                               for cid in people[pid].children_ids if cid != person.id)
            if siblings_count == 0:
                people_no_siblings.append(person.first_name)
    
    if people_no_siblings:
        questions.append({
            "question": get_translation("q_no_siblings", language),
            "answer": format_answer(people_no_siblings, language),
            "type": "negation"
        })
    
    # 3. Qui a des enfants mais pas de petits-enfants
    parents_no_grandchildren = []
    for person in people.values():
        if person.children_ids:
            has_grandchildren = any(people[cid].children_ids for cid in person.children_ids)
            if not has_grandchildren:
                parents_no_grandchildren.append(person.first_name)
    
    if parents_no_grandchildren:
        questions.append({
            "question": get_translation("q_has_children_no_grandchildren", language),
            "answer": format_answer(parents_no_grandchildren, language),
            "type": "negation"
        })
    
    # 4. Génération ne travaillant ni comme avocat ni comme médecin
    generations = {}
    for person in people.values():
        if person.generation not in generations:
            generations[person.generation] = []
        generations[person.generation].append(person)
    
    for person in people.values():
        same_gen = generations.get(person.generation, [])
        not_lawyer_doctor = [p.first_name for p in same_gen 
                           if p.profession not in ["avocat", "médecin", "lawyer", "doctor"]]
        
        if not_lawyer_doctor and len(not_lawyer_doctor) < len(same_gen):
            questions.append({
                "question": get_translation("q_generation_not_lawyer_doctor", language).format(name=person.first_name),
                "answer": format_answer(not_lawyer_doctor, language),
                "type": "negation"
            })
            break  # Une seule question de ce type
    
    return questions


def generate_comparative_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions comparatives complexes."""
    questions = []
    
    # 1. Qui a le plus de descendants
    descendants_count = {}
    for person in people.values():
        count = 0
        # Compter tous les descendants récursivement
        def count_descendants(p_id):
            nonlocal count
            for cid in people[p_id].children_ids:
                count += 1
                count_descendants(cid)
        
        count_descendants(person.id)
        if count > 0:
            descendants_count[person.first_name] = count
    
    if descendants_count:
        max_count = max(descendants_count.values())
        most_descendants = [name for name, count in descendants_count.items() if count == max_count]
        questions.append({
            "question": get_translation("q_most_descendants", language),
            "answer": format_answer(most_descendants, language),
            "type": "comparative"
        })
    
    # 2. Quelle génération a le plus de blonds
    generations_blond = {}
    for person in people.values():
        if person.hair_color in ["blond", "blonde"]:
            if person.generation not in generations_blond:
                generations_blond[person.generation] = 0
            generations_blond[person.generation] += 1
    
    if generations_blond:
        max_blond = max(generations_blond.values())
        best_gen = [str(gen) for gen, count in generations_blond.items() if count == max_blond]
        questions.append({
            "question": get_translation("q_generation_most_blond", language),
            "answer": format_answer(best_gen, language),
            "type": "comparative"
        })
    
    # 3. Qui a autant d'enfants que X
    for person in people.values():
        if person.children_ids:
            same_count = [p.first_name for p in people.values() 
                         if p.id != person.id and len(p.children_ids) == len(person.children_ids)]
            if same_count:
                questions.append({
                    "question": get_translation("q_same_number_children_as", language).format(name=person.first_name),
                    "answer": format_answer(same_count, language),
                    "type": "comparative"
                })
    
    # 4. Qui a plus de petits-fils que de petites-filles
    more_grandsons = []
    for person in people.values():
        grandsons = 0
        granddaughters = 0
        for cid in person.children_ids:
            for gcid in people[cid].children_ids:
                if people[gcid].gender == 'M':
                    grandsons += 1
                else:
                    granddaughters += 1
        
        if grandsons > granddaughters and grandsons > 0:
            more_grandsons.append(person.first_name)
    
    if more_grandsons:
        questions.append({
            "question": get_translation("q_more_grandsons_than_granddaughters", language),
            "answer": format_answer(more_grandsons, language),
            "type": "comparative"
        })
    
    return questions


def generate_relational_path_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions sur les chemins relationnels."""
    questions = []
    
    # Helper pour trouver le chemin entre deux personnes
    def find_relationship(p1_id: str, p2_id: str) -> str:
        p1 = people[p1_id]
        p2 = people[p2_id]
        
        # Relations directes
        if p2_id in p1.children_ids:
            return "parent-enfant"
        if p1_id in p2.children_ids:
            return "enfant-parent"
        
        # Frères/sœurs
        if p1.parent_ids and p2.parent_ids:
            if set(p1.parent_ids) == set(p2.parent_ids):
                return "frère/sœur"
        
        # Grands-parents/petits-enfants
        for cid in p1.children_ids:
            if p2_id in people[cid].children_ids:
                return "grand-parent"
        for cid in p2.children_ids:
            if p1_id in people[cid].children_ids:
                return "petit-enfant"
        
        # Oncle-tante/neveu-nièce
        if p1.parent_ids:
            for pid in p1.parent_ids:
                parent = people[pid]
                if parent.parent_ids:
                    for gpid in parent.parent_ids:
                        for uncle_id in people[gpid].children_ids:
                            if uncle_id != pid and uncle_id == p2_id:
                                return "neveu/nièce-oncle/tante"
        
        # Cousins
        p1_grandparents = []
        p2_grandparents = []
        for pid in p1.parent_ids:
            p1_grandparents.extend(people[pid].parent_ids)
        for pid in p2.parent_ids:
            p2_grandparents.extend(people[pid].parent_ids)
        
        if set(p1_grandparents) & set(p2_grandparents):
            return "cousins"
        
        return "non apparentés"
    
    # Générer quelques paires intéressantes
    person_list = list(people.values())
    if len(person_list) >= 2:
        # Sélectionner des paires spécifiques pour garantir des relations intéressantes
        generated_pairs = set()
        
        # 1. Quelques paires parent-enfant
        for person in people.values():
            if person.children_ids and len(questions) < 5:
                child = people[person.children_ids[0]]
                pair = tuple(sorted([person.id, child.id]))
                if pair not in generated_pairs:
                    generated_pairs.add(pair)
                    questions.append({
                        "question": get_translation("q_relationship_between", language).format(
                            name1=person.first_name, name2=child.first_name),
                        "answer": "parent-enfant",
                        "type": "relational_path"
                    })
        
        # 2. Quelques paires de cousins si possible
        for person in people.values():
            # Trouver les cousins
            cousins = []
            if person.parent_ids:
                for pid in person.parent_ids:
                    parent = people[pid]
                    if parent.parent_ids:
                        for gpid in parent.parent_ids:
                            for aunt_uncle_id in people[gpid].children_ids:
                                if aunt_uncle_id != pid:
                                    for cousin_id in people[aunt_uncle_id].children_ids:
                                        cousins.append(people[cousin_id])
            
            if cousins and len(questions) < 10:
                cousin = cousins[0]
                pair = tuple(sorted([person.id, cousin.id]))
                if pair not in generated_pairs:
                    generated_pairs.add(pair)
                    questions.append({
                        "question": get_translation("q_relationship_between", language).format(
                            name1=person.first_name, name2=cousin.first_name),
                        "answer": "cousins",
                        "type": "relational_path"
                    })
                    
                    # Générations entre eux
                    gen_diff = abs(person.generation - cousin.generation)
                    questions.append({
                        "question": get_translation("q_generations_between", language).format(
                            name1=person.first_name, name2=cousin.first_name),
                        "answer": str(gen_diff),
                        "type": "relational_path"
                    })
    
    return questions