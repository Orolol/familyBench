"""Questions énigmes complexes avec enchaînement de conditions."""

import random
from typing import Dict, List, Any, Tuple
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import get_common_attributes, get_father, get_mother


def generate_enigma_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions énigmes complexes avec enchaînement de conditions."""
    questions = []
    
    # Helper pour suivre une chaîne de relations
    def follow_relation_chain(start_person: Person, chain: List[tuple]) -> List[Person]:
        """Suit une chaîne de relations et retourne les personnes finales."""
        current_people = [start_person]
        
        for relation_type, filter_attr, filter_value in chain:
            next_people = []
            
            for person in current_people:
                if relation_type == "brother":
                    if person.parent_ids:
                        siblings = [people[cid] for pid in person.parent_ids 
                                  for cid in people[pid].children_ids 
                                  if cid != person.id and people[cid].gender == 'M']
                        next_people.extend(siblings)
                
                elif relation_type == "sister":
                    if person.parent_ids:
                        siblings = [people[cid] for pid in person.parent_ids 
                                  for cid in people[pid].children_ids 
                                  if cid != person.id and people[cid].gender == 'F']
                        next_people.extend(siblings)
                
                elif relation_type == "father":
                    father = get_father(person, people)
                    if father:
                        next_people.append(father)
                
                elif relation_type == "mother":
                    mother = get_mother(person, people)
                    if mother:
                        next_people.append(mother)
                
                elif relation_type == "parent":
                    next_people.extend([people[pid] for pid in person.parent_ids])
                
                elif relation_type == "child":
                    next_people.extend([people[cid] for cid in person.children_ids])
                
                elif relation_type == "cousin":
                    if person.parent_ids:
                        for pid in person.parent_ids:
                            parent = people[pid]
                            if parent.parent_ids:
                                for gpid in parent.parent_ids:
                                    for aunt_uncle_id in people[gpid].children_ids:
                                        if aunt_uncle_id != pid:
                                            for cousin_id in people[aunt_uncle_id].children_ids:
                                                next_people.append(people[cousin_id])
                
                elif relation_type == "grandparent":
                    for pid in person.parent_ids:
                        next_people.extend([people[gpid] for gpid in people[pid].parent_ids])
                
                elif relation_type == "grandchild":
                    for cid in person.children_ids:
                        next_people.extend([people[gcid] for gcid in people[cid].children_ids])
            
            # Appliquer le filtre si spécifié
            if filter_attr and filter_value:
                next_people = [p for p in next_people if getattr(p, filter_attr) == filter_value]
            
            current_people = list(set(next_people))  # Éliminer les doublons
            
            if not current_people:
                return []
        
        return current_people
    
    # Générer des énigmes avec différentes complexités
    person_list = list(people.values())
    
    # Énigmes de niveau 1 : relation + attribut final
    for _ in range(5):
        person = random.choice(person_list)
        
        # Choisir une personne avec des attributs distinctifs
        target_people = [p for p in people.values() 
                        if p.hair_color and p.profession and len(p.parent_ids) > 0]
        
        if target_people:
            target = random.choice(target_people)
            
            # Construire la question
            relation_parts = []
            
            # Ajouter l'attribut final
            attr_type = random.choice(['hair_color', 'profession', 'eye_color'])
            if attr_type == 'hair_color':
                attr_desc = get_translation("with_hair", language).format(color=getattr(target, attr_type))
            elif attr_type == 'profession':
                # Utiliser seulement les professions communes
                common_profs = get_common_attributes(people, 'profession', min_count=3)
                if target.profession in common_profs:
                    attr_desc = get_translation("working_as", language).format(profession=target.profession)
                else:
                    continue
            else:
                attr_desc = get_translation("with_eyes", language).format(color=getattr(target, attr_type))
            
            # Trouver un chemin vers cette personne
            # Exemple simple : "Qui est le frère du père aux cheveux roux ?"
            if target.parent_ids:
                parent = people[random.choice(target.parent_ids)]
                if parent.children_ids and len(parent.children_ids) > 1:
                    # Il a des frères/sœurs
                    siblings = [people[cid] for cid in parent.children_ids if cid != target.id]
                    if siblings:
                        if target.gender == 'M':
                            relation_chain = get_translation("the_brother_of", language) + " " + parent.first_name + " " + attr_desc
                        else:
                            relation_chain = get_translation("the_sister_of", language) + " " + parent.first_name + " " + attr_desc
                        
                        questions.append({
                            "question": get_translation("q_enigma_base", language).format(relation_chain=relation_chain),
                            "answer": target.first_name,
                            "type": "enigme",
                            "complexity": 1
                        })
    
    # Énigmes de niveau 2 : 2 relations enchaînées
    for _ in range(5):
        # Trouver des personnes avec des petits-enfants
        grandparents = [p for p in people.values() 
                       if any(people[cid].children_ids for cid in p.children_ids)]
        
        if grandparents:
            grandparent = random.choice(grandparents)
            # Trouver un petit-enfant
            grandchildren = []
            for cid in grandparent.children_ids:
                grandchildren.extend([people[gcid] for gcid in people[cid].children_ids])
            
            if grandchildren:
                grandchild = random.choice(grandchildren)
                parent = None
                for cid in grandparent.children_ids:
                    if grandchild.id in people[cid].children_ids:
                        parent = people[cid]
                        break
                
                if parent:
                    # "Qui est l'enfant du fils de X ?"
                    if parent.gender == 'M':
                        relation_chain = f"{get_translation('the_child_of', language)} {get_translation('the_son_of', language)} {grandparent.first_name}"
                    else:
                        relation_chain = f"{get_translation('the_child_of', language)} {get_translation('the_daughter_of', language)} {grandparent.first_name}"
                    
                    # Si plusieurs petits-enfants, spécifier un attribut
                    if len(grandchildren) > 1:
                        attr_desc = get_translation("with_hair", language).format(color=grandchild.hair_color)
                        relation_chain += " " + attr_desc
                    
                    questions.append({
                        "question": get_translation("q_enigma_base", language).format(relation_chain=relation_chain),
                        "answer": grandchild.first_name,
                        "type": "enigme",
                        "complexity": 2
                    })
    
    # Énigmes de niveau 3 : 3+ relations ou conditions multiples
    for _ in range(5):
        # Chercher des cousins avec des attributs spécifiques
        for person in people.values():
            cousins = []
            if person.parent_ids:
                for pid in person.parent_ids:
                    parent = people[pid]
                    if parent.parent_ids:
                        for gpid in parent.parent_ids:
                            grandparent = people[gpid]
                            for aunt_uncle_id in grandparent.children_ids:
                                if aunt_uncle_id != pid:
                                    aunt_uncle = people[aunt_uncle_id]
                                    for cousin_id in aunt_uncle.children_ids:
                                        cousins.append(people[cousin_id])
            
            if cousins:
                # Filtrer par attribut
                red_hair_cousins = [c for c in cousins if c.hair_color in ["roux", "red"]]
                if red_hair_cousins and person.parent_ids:
                    cousin = red_hair_cousins[0]
                    parent = people[person.parent_ids[0]]
                    
                    # "Qui est le cousin du fils de X aux cheveux roux ?"
                    if person.gender == 'M':
                        relation_chain = f"{get_translation('the_cousin_of', language)} {get_translation('the_son_of', language)} {parent.first_name} {get_translation('with_hair', language).format(color=cousin.hair_color)}"
                    else:
                        relation_chain = f"{get_translation('the_cousin_of', language)} {get_translation('the_daughter_of', language)} {parent.first_name} {get_translation('with_hair', language).format(color=cousin.hair_color)}"
                    
                    questions.append({
                        "question": get_translation("q_enigma_base", language).format(relation_chain=relation_chain),
                        "answer": cousin.first_name,
                        "type": "enigme",
                        "complexity": 3
                    })
                    break
    
    return questions