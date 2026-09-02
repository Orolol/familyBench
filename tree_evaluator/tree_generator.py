import logging
import random
import uuid
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

from tree_evaluator.models import Person

logger = logging.getLogger(__name__)

# Dossier des données, indépendant du répertoire courant
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def actual_depth(people: Dict[str, Person]) -> int:
    """Nombre de générations réellement présentes dans l'arbre."""
    if not people:
        return 0
    return max(p.generation for p in people.values()) + 1

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

DEFAULT_SECOND_UNION_PERCENTAGE = 20


def generate_tree(
    total_people: int,
    max_depth: int,
    max_children_per_person: int = 2,
    seed: int | None = None,
    num_root_couples: int = 1,
    language: str = "fr",
    second_union_percentage: int = DEFAULT_SECOND_UNION_PERCENTAGE,
) -> Dict[str, Person]:
    """Génère un arbre généalogique aléatoire.

    Args:
        max_children_per_person: nombre max d'enfants PAR UNION (par couple).
        second_union_percentage: part (0-100) des personnes qui, après une
            première union, ont aussi des enfants avec un second partenaire.
            Cela crée des demi-frères/sœurs et des beaux-parents. Chaque
            enfant a toujours exactement deux parents.
    """
    
    if total_people < 1:
        raise ValueError("total_people must be at least 1")
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    if max_children_per_person < 1:
        raise ValueError("max_children_per_person must be at least 1")
    if num_root_couples < 1:
        raise ValueError("num_root_couples must be at least 1")
    if language not in ("fr", "en"):
        raise ValueError(f"language must be 'fr' or 'en', got {language!r}")
    if not 0 <= second_union_percentage <= 100:
        raise ValueError("second_union_percentage must be between 0 and 100")
    
    if seed is not None:
        random.seed(seed)

    # Charger les données selon la langue
    data_dir = DATA_DIR / language
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
        
        def make_union(person: Person) -> bool:
            """Marie `person` avec un partenaire du pool et leur donne 1..max enfants."""
            potential_partners = [p for p in person_pool if p.gender != person.gender]
            if not potential_partners or len(person_pool) < 2:
                return False
            partner = random.choice(potential_partners)
            person_pool.remove(partner)
            partner.generation = person.generation  # Le partenaire rejoint la même génération
            people_in_tree_ids.add(partner.id)
            if person.gender == 'M':
                parent1, parent2 = person, partner
            else:
                parent1, parent2 = partner, person
            max_possible_children = min(max_children_per_person, len(person_pool))
            if max_possible_children == 0:
                return False
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
            return True

        for person in people_to_marry:
            # Il faut au moins un conjoint ET un enfant, sinon le conjoint
            # entrerait dans l'arbre sans aucun lien de parenté.
            if len(person_pool) < 2:
                break
            if not make_union(person):
                continue
            # Seconde union : demi-frères/sœurs et beaux-parents
            if random.random() * 100 < second_union_percentage and len(person_pool) >= 2:
                make_union(person)

        if not next_generation:
            break
        
        current_generation = next_generation
        gen += 1

    # Rattacher les personnes restantes (pool non vide à cause de la limite de
    # profondeur ou d'un reste impair) comme enfants de couples existants qui
    # ont encore de la place, pour que l'arbre contienne bien total_people.
    if person_pool:
        random.shuffle(person_pool)
        for leftover in list(person_pool):
            candidates = [
                p for p in people.values()
                if p.id in people_in_tree_ids
                and p.children_ids
                and len(p.children_ids) < max_children_per_person
                and p.generation <= max_depth - 2
            ]
            if not candidates:
                break
            parent = random.choice(candidates)
            first_child = people[parent.children_ids[0]]
            co_parent_id = next(pid for pid in first_child.parent_ids if pid != parent.id)
            co_parent = people[co_parent_id]
            leftover.generation = parent.generation + 1
            leftover.parent_ids = [parent.id, co_parent_id] if parent.gender == 'M' else [co_parent_id, parent.id]
            parent.children_ids.append(leftover.id)
            co_parent.children_ids.append(leftover.id)
            people_in_tree_ids.add(leftover.id)
            person_pool.remove(leftover)
        if person_pool:
            logger.warning(
                "%d of %d people could not be placed in the tree (depth %d, max %d children per couple) "
                "and were dropped.", len(person_pool), total_people, max_depth, max_children_per_person,
            )

    final_tree = {pid: p for pid, p in people.items() if pid in people_in_tree_ids}

    depth_reached = actual_depth(final_tree)
    if depth_reached < max_depth:
        logger.warning(
            "Requested depth %d but the tree only has %d generation(s): the pool of %d people "
            "is exhausted before reaching it (each couple has 1-%d children). Increase "
            "total_people or lower max_children_per_person / num_root_couples to go deeper.",
            max_depth, depth_reached, total_people, max_children_per_person,
        )

    return final_tree