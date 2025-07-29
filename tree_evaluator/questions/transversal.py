"""Questions transversales et verticales."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer


def generate_transversal_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions transversales (même génération avec critères)."""
    questions = []
    
    # Grouper les personnes par génération
    generations = {}
    for person in people.values():
        if person.generation not in generations:
            generations[person.generation] = []
        generations[person.generation].append(person)
    
    for person in people.values():
        gen_level = person.generation
        same_gen_people = generations.get(gen_level, [])
        
        if len(same_gen_people) > 1:
            # Questions sur même génération avec genre
            males_same_gen = [p.first_name for p in same_gen_people if p.gender == 'M' and p.id != person.id]
            females_same_gen = [p.first_name for p in same_gen_people if p.gender == 'F' and p.id != person.id]
            
            if males_same_gen:
                questions.append({
                    "question": get_translation("q_men_same_generation", language).format(name=person.first_name),
                    "answer": format_answer(males_same_gen, language),
                    "type": "transversale_generation"
                })
            
            if females_same_gen:
                questions.append({
                    "question": get_translation("q_women_same_generation", language).format(name=person.first_name),
                    "answer": format_answer(females_same_gen, language),
                    "type": "transversale_generation"
                })
    
    return questions


def generate_vertical_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions verticales (ancêtres les plus vieux, descendants)."""
    questions = []
    
    def get_oldest_ancestors(person_id: str, people: Dict[str, Person]) -> List[str]:
        """Trouve les ancêtres les plus vieux (sans parents) d'une personne."""
        person = people[person_id]
        if not person.parent_ids:
            return [person.first_name]
        
        ancestors = []
        for parent_id in person.parent_ids:
            ancestors.extend(get_oldest_ancestors(parent_id, people))
        
        return list(set(ancestors))
    
    def get_all_descendants(person_id: str, people: Dict[str, Person]) -> List[str]:
        """Trouve tous les descendants d'une personne."""
        person = people[person_id]
        descendants = []
        
        for child_id in person.children_ids:
            child = people[child_id]
            descendants.append(child.first_name)
            descendants.extend(get_all_descendants(child_id, people))
        
        return descendants
    
    for person in people.values():
        # Questions sur les ancêtres les plus vieux
        if person.parent_ids:
            oldest_ancestors = get_oldest_ancestors(person.id, people)
            if oldest_ancestors:
                questions.append({
                    "question": get_translation("q_oldest_ancestors", language).format(name=person.first_name),
                    "answer": format_answer(oldest_ancestors, language),
                    "type": "verticale_ancetre"
                })
        
        # Questions sur tous les descendants
        all_descendants = get_all_descendants(person.id, people)
        if all_descendants:
            questions.append({
                "question": get_translation("q_all_descendants", language).format(name=person.first_name),
                "answer": format_answer(all_descendants, language),
                "type": "verticale_descendant"
            })
            
            # Descendants avec critères
            descendants_by_profession = {}
            for desc_name in all_descendants:
                for p in people.values():
                    if p.first_name == desc_name:
                        if p.profession not in descendants_by_profession:
                            descendants_by_profession[p.profession] = []
                        descendants_by_profession[p.profession].append(p.first_name)
                        break
            
            for profession, names in descendants_by_profession.items():
                if names and len(names) > 1:
                    questions.append({
                        "question": get_translation("q_descendants_profession", language).format(name=person.first_name, profession=profession),
                        "answer": format_answer(names, language),
                        "type": "verticale_descendant_critere"
                    })
    
    # Questions sur les personnes sans parents (racines de l'arbre)
    root_people = [p.first_name for p in people.values() if not p.parent_ids]
    if len(root_people) > 1:
        questions.append({
            "question": get_translation("q_people_without_parents", language),
            "answer": format_answer(root_people, language),
            "type": "verticale_racine"
        })
        
        # Racines par profession
        root_by_profession = {}
        for p in people.values():
            if not p.parent_ids:
                if p.profession not in root_by_profession:
                    root_by_profession[p.profession] = []
                root_by_profession[p.profession].append(p.first_name)
        
        for profession, names in root_by_profession.items():
            if names and len(names) > 1:
                questions.append({
                    "question": get_translation("q_people_without_parents_profession", language).format(profession=profession),
                    "answer": format_answer(names, language),
                    "type": "verticale_racine_critere"
                })
    
    # Questions sur les personnes sans enfants (feuilles de l'arbre)
    leaf_people = [p.first_name for p in people.values() if not p.children_ids]
    if len(leaf_people) > 1:
        questions.append({
            "question": get_translation("q_people_without_children", language),
            "answer": format_answer(leaf_people, language),
            "type": "verticale_feuille"
        })
    
    return questions