import random
import uuid
from itertools import product
from typing import Dict, List, Tuple

from tree_evaluator.models import Person

def _load_data(file_path: str) -> List[Tuple[str, str]]:
    """Charge les lignes d'un fichier texte (prénom,sexe)."""
    with open(file_path, "r", encoding="utf-8") as f:
        return [tuple(line.strip().split(',')) for line in f if line.strip()]

def _load_professions(file_path: str) -> List[str]:
    """Charge les lignes d'un fichier texte."""
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def _get_unique_attributes(
    first_names_genders: List[Tuple[str, str]],
    professions: List[str],
    hair_colors: List[str],
    eye_colors: List[str],
    hat_colors: List[str],
    total_people: int,
) -> Tuple[List[Tuple[str, str]], List[str], List[Tuple[str, str, str]]]:
    """Génère des ensembles d'attributs pour chaque personne."""
    
    if len(first_names_genders) < total_people:
        raise ValueError("Pas assez de prénoms uniques pour le nombre de personnes demandé.")
    
    unique_names_genders = random.sample(first_names_genders, total_people)
    
    # Les professions ne sont plus uniques - on peut avoir plusieurs personnes avec la même profession
    selected_professions = [random.choice(professions) for _ in range(total_people)]

    color_combinations = list(product(hair_colors, eye_colors, hat_colors))
    if len(color_combinations) < total_people:
        raise ValueError("Pas assez de combinaisons de couleurs uniques pour le nombre de personnes demandé.")
    
    unique_color_combos = random.sample(color_combinations, total_people)
    
    return unique_names_genders, selected_professions, unique_color_combos

def generate_tree(
    total_people: int,
    max_depth: int,
    max_children_per_person: int,
    seed: int | None = None,
    num_root_couples: int = 1,
    language: str = "fr",
) -> Dict[str, Person]:
    
    if seed is not None:
        random.seed(seed)

    # Charger les données selon la langue
    data_dir = f"data/{language}"
    first_names_genders = _load_data(f"{data_dir}/first_names.txt")
    professions = _load_professions(f"{data_dir}/professions.txt")
    hair_colors = _load_professions(f"{data_dir}/hair_colors.txt")
    eye_colors = _load_professions(f"{data_dir}/eye_colors.txt")
    hat_colors = _load_professions(f"{data_dir}/hat_colors.txt")

    unique_names_genders, selected_professions, unique_color_combos = _get_unique_attributes(
        first_names_genders, professions, hair_colors, eye_colors, hat_colors, total_people
    )

    people: Dict[str, Person] = {}
    person_pool = []
    for i in range(total_people):
        person_id = str(uuid.uuid4())
        name, gender = unique_names_genders[i]
        hair, eyes, hat = unique_color_combos[i]
        person = Person(
            id=person_id,
            first_name=name,
            gender=gender,
            profession=selected_professions[i],
            hair_color=hair,
            eye_color=eyes,
            hat_color=hat,
        )
        people[person_id] = person
        person_pool.append(person)

    if total_people < 2:
        return people

    males = [p for p in person_pool if p.gender == 'M']
    females = [p for p in person_pool if p.gender == 'F']

    if not males or not females:
        raise ValueError("Impossible de former un couple fondateur. Assurez-vous d'avoir des hommes et des femmes dans la liste de prénoms.")

    # Créer plusieurs couples racines
    current_generation = []
    people_in_tree_ids = set()
    
    num_couples_to_create = min(num_root_couples, len(males), len(females))
    
    for _ in range(num_couples_to_create):
        if not males or not females:
            break
            
        gen0_p1 = males.pop(0)
        gen0_p2 = females.pop(0)
        person_pool.remove(gen0_p1)
        person_pool.remove(gen0_p2)
        
        gen0_p1.generation = 0
        gen0_p2.generation = 0
        
        current_generation.extend([gen0_p1, gen0_p2])
        people_in_tree_ids.add(gen0_p1.id)
        people_in_tree_ids.add(gen0_p2.id)
    
    gen = 0
    while person_pool and gen < (max_depth - 1):
        next_generation = []
        
        # Pour chaque personne de la génération actuelle, on essaie de lui trouver un partenaire du pool
        people_to_marry = list(current_generation)
        random.shuffle(people_to_marry)
        
        for person in people_to_marry:
            if not person_pool:
                break
                
            # Chercher un partenaire de sexe opposé dans le pool
            potential_partners = [p for p in person_pool if p.gender != person.gender]
            
            if not potential_partners:
                continue
                
            # Choisir un partenaire au hasard
            partner = random.choice(potential_partners)
            person_pool.remove(partner)
            partner.generation = person.generation  # Le partenaire rejoint la même génération
            people_in_tree_ids.add(partner.id)
            
            # Décider qui est parent1 et parent2 selon le genre
            if person.gender == 'M':
                parent1, parent2 = person, partner
            else:
                parent1, parent2 = partner, person
            
            # Avoir des enfants
            max_possible_children = min(max_children_per_person, len(person_pool)) if person_pool else 0
            if max_possible_children == 0:
                continue
            num_children = random.randint(1, max_possible_children)
            
            for _ in range(num_children):
                if not person_pool:
                    break
                
                child = person_pool.pop(0)
                child.generation = gen + 1
                child.parent_ids = [parent1.id, parent2.id]
                parent1.children_ids.append(child.id)
                parent2.children_ids.append(child.id)
                
                next_generation.append(child)
                people_in_tree_ids.add(child.id)
        
        if not next_generation:
            break
        
        current_generation = next_generation
        gen += 1

    final_tree = {pid: p for pid, p in people.items() if pid in people_in_tree_ids}
    
    return final_tree