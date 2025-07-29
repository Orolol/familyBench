"""Questions de recherche par attribut."""

from typing import Dict, List, Any
from tree_evaluator.models import Person
from tree_evaluator.translations import get_translation
from .base import format_answer, get_common_attributes


def generate_attribute_search_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions de recherche par attribut."""
    questions = []
    attributes = ["hair_color", "eye_color", "hat_color", "profession"]

    for attr in attributes:
        all_values = {getattr(p, attr) for p in people.values()}
        # Pour les professions, n'utiliser que les communes
        if attr == "profession":
            common_values = get_common_attributes(people, attr, min_count=3)
            all_values = [v for v in all_values if v in common_values]
        
        for value in all_values:
            matching_people = [p.first_name for p in people.values() if getattr(p, attr) == value]
            if attr == "profession":
                # Ne générer la question que s'il y a au moins 2 personnes avec cette profession
                if len(matching_people) >= 2:
                    question_text = get_translation("q_who_works_as", language).format(profession=value)
                else:
                    continue
            elif attr == "hat_color":
                question_text = get_translation("q_who_has_hat", language).format(color=value)
            elif attr == "hair_color":
                question_text = get_translation("q_who_has_hair", language).format(color=value)
            elif attr == "eye_color":
                question_text = get_translation("q_who_has_eyes", language).format(color=value)
            
            questions.append({
                "question": question_text,
                "answer": format_answer(matching_people, language),
                "type": "recherche_attributs",
            })
    return questions


def generate_multi_criteria_questions(people: Dict[str, Person], language: str = "fr") -> List[Dict[str, Any]]:
    """Génère des questions de recherche multi-critères."""
    questions = []
    
    # Questions cheveux + yeux (limiter le nombre)
    generated_combinations = set()
    for p1 in people.values():
        combo = (p1.hair_color, p1.eye_color)
        if combo not in generated_combinations:
            generated_combinations.add(combo)
            matches = [p.first_name for p in people.values() 
                      if p.hair_color == p1.hair_color and p.eye_color == p1.eye_color]
            if len(matches) > 1:  # Au moins 2 personnes
                questions.append({
                    "question": get_translation("q_who_has_hair_and_eyes", language).format(hair=p1.hair_color, eyes=p1.eye_color),
                    "answer": format_answer(matches, language),
                    "type": "recherche_multi_criteres"
                })
    
    # Ajouter des questions avec 3 critères
    for person in people.values():
        # Cheveux + yeux + chapeau
        matches = [p.first_name for p in people.values() 
                  if p.hair_color == person.hair_color and 
                     p.eye_color == person.eye_color and 
                     p.hat_color == person.hat_color]
        if len(matches) > 1 and len(matches) < 5:  # Entre 2 et 4 personnes
            questions.append({
                "question": f"Qui a les cheveux {person.hair_color}, les yeux {person.eye_color} et porte un chapeau {person.hat_color} ?",
                "answer": format_answer(matches, language),
                "type": "recherche_multi_criteres"
            })
            break  # Limiter le nombre
    
    return questions