import random
from typing import Dict, List
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation

def convert_tree_to_text(people: Dict[str, Person], shuffle: bool = False, language: str = "fr") -> str:
    """Convertit le dictionnaire de personnes en une description textuelle.
    
    Args:
        people: Dictionnaire des personnes
        shuffle: Si True, mélange l'ordre des personnes et des informations
    """
    if not people:
        return ""

    # Obtenir la liste des personnes
    people_list = list(people.values())
    
    if shuffle:
        # Mélanger complètement l'ordre des personnes
        random.shuffle(people_list)
    else:
        # Ordre par défaut : par génération puis par prénom
        people_list = sorted(people_list, key=lambda p: (p.generation, p.first_name))

    description_parts = []
    
    for person in people_list:
        person_parts = []
        
        # Description des attributs
        if language == "en":
            # Format anglais : combine toutes les parties en une seule phrase
            attr_part = (
                f"{get_translation('has_hair', language).format(name=f'{person.first_name} ({person.gender})', hair_color=person.hair_color)}, "
                f"{get_translation('has_eyes', language).format(eye_color=person.eye_color)}, "
                f"{get_translation('wears_hat', language).format(hat_color=person.hat_color)} and "
                f"{get_translation('works_as', language).format(profession=person.profession)}."
            )
        else:
            # Format français : utilise les conjonctions françaises
            attr_part = (
                f"{get_translation('has_hair', language).format(name=f'{person.first_name} ({person.gender})', hair_color=person.hair_color)}, "
                f"{get_translation('has_eyes', language).format(eye_color=person.eye_color)}, "
                f"{get_translation('wears_hat', language).format(hat_color=person.hat_color)} et "
                f"{get_translation('works_as', language).format(profession=person.profession)}."
            )
        person_parts.append(attr_part)

        # Description des parents
        if person.parent_ids:
            parent_names = sorted([f'{people[pid].first_name} ({people[pid].gender})' for pid in person.parent_ids])
            parent_part = get_translation('is_child_of', language).format(
                name=f'{person.first_name} ({person.gender})',
                parent1=parent_names[0],
                parent2=parent_names[1]
            ) + "."
            person_parts.append(parent_part)

        # Description des enfants
        if person.children_ids:
            children_names = sorted([f'{people[cid].first_name} ({people[cid].gender})' for cid in person.children_ids])
            num_children = len(children_names)
            if num_children == 1:
                child_part = get_translation('has_children_singular', language).format(
                    name=f'{person.first_name} ({person.gender})',
                    children=children_names[0]
                ) + "."
            else:
                child_part = get_translation('has_children_plural', language).format(
                    name=f'{person.first_name} ({person.gender})',
                    count=num_children,
                    children=', '.join(children_names)
                ) + "."
            person_parts.append(child_part)
        
        if shuffle:
            # Mélanger l'ordre des informations pour chaque personne
            # Mais toujours garder les attributs en premier
            if len(person_parts) > 1:
                other_parts = person_parts[1:]
                random.shuffle(other_parts)
                person_parts = [person_parts[0]] + other_parts
        
        description_parts.extend(person_parts)

    return "\n".join(description_parts)
