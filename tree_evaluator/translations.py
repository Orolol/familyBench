"""Module de traductions pour TreeEval."""

TRANSLATIONS = {
    "fr": {
        # Templates pour text_converter
        "has_hair": "{name} a les cheveux {hair_color}",
        "has_eyes": "les yeux {eye_color}",
        "wears_hat": "porte un chapeau {hat_color}",
        "works_as": "travaille comme {profession}",
        "has_children_singular": "{name} a 1 enfant : {children}",
        "has_children_plural": "{name} a {count} enfant(s) : {children}",
        "is_child_of": "{name} est l'enfant de {parent1} et {parent2}",
        
        # Templates pour les questions
        "q_children_of": "Qui sont les enfants de {name} ?",
        "q_parents_of": "Qui sont les parents de {name} ?",
        "q_father_of": "Qui est le père de {name} ?",
        "q_mother_of": "Qui est la mère de {name} ?",
        "q_child_of_whom": "De qui {name} est-{pronoun} l'enfant ?",
        "q_parent_of_whom": "De qui {name} est-{pronoun} le parent ?",
        "q_who_works_as": "Qui travaille comme {profession} ?",
        "q_who_has_hat": "Qui porte un chapeau {color} ?",
        "q_who_has_hair": "Qui a les cheveux {color} ?",
        "q_who_has_eyes": "Qui a les yeux {color} ?",
        "q_who_has_hair_and_eyes": "Qui a les cheveux {hair} et les yeux {eyes} ?",
        "q_how_many_children": "Combien d'enfants a {name} ?",
        "q_how_many_with_eyes": "Combien de personnes ont les yeux {color} ?",
        "q_how_many_profession": "Combien de {profession} y a-t-il ?",
        "q_siblings_of": "Qui sont les frères et sœurs de {name} ?",
        "q_brothers_of": "Qui sont les frères de {name} ?",
        "q_sisters_of": "Qui sont les sœurs de {name} ?",
        "q_grandparents_of": "Qui sont les grands-parents de {name} ?",
        "q_grandfathers_of": "Qui sont les grands-pères de {name} ?",
        "q_grandmothers_of": "Qui sont les grands-mères de {name} ?",
        "q_grandchildren_of": "Qui sont les petits-enfants de {name} ?",
        "q_grandsons_of": "Qui sont les petits-fils de {name} ?",
        "q_granddaughters_of": "Qui sont les petites-filles de {name} ?",
        "q_same_generation_profession": "Qui est de la même génération que {name} et travaille comme {profession} ?",
        "q_same_generation_hair": "Qui est de la même génération que {name} et a les cheveux {color} ?",
        "q_men_same_generation": "Quels hommes sont de la même génération que {name} ?",
        "q_women_same_generation": "Quelles femmes sont de la même génération que {name} ?",
        "q_oldest_ancestors": "Qui sont les plus vieux ancêtres de {name} ?",
        "q_all_descendants": "Qui sont tous les descendants de {name} ?",
        "q_descendants_profession": "Quels descendants de {name} travaillent comme {profession} ?",
        "q_people_without_parents": "Qui sont les personnes sans parents dans cet arbre ?",
        "q_people_without_children": "Qui sont les personnes sans enfants dans cet arbre ?",
        "q_great_grandparents": "Qui sont les arrière-grands-parents de {name} ?",
        "q_great_grandfathers": "Qui sont les arrière-grands-pères de {name} ?",
        "q_great_grandmothers": "Qui sont les arrière-grands-mères de {name} ?",
        "q_great_grandchildren": "Qui sont les arrière-petits-enfants de {name} ?",
        "q_great_grandsons": "Qui sont les arrière-petits-fils de {name} ?",
        "q_great_granddaughters": "Qui sont les arrière-petites-filles de {name} ?",
        "q_uncles_aunts": "Qui sont les oncles et tantes de {name} ?",
        "q_uncles": "Qui sont les oncles de {name} ?",
        "q_aunts": "Qui sont les tantes de {name} ?",
        "q_cousins_all": "Qui sont les cousins et cousines de {name} ?",
        "q_cousins_male": "Qui sont les cousins de {name} ?",
        "q_cousins_female": "Qui sont les cousines de {name} ?",
        "q_nephews_nieces": "Qui sont les neveux et nièces de {name} ?",
        "q_nephews": "Qui sont les neveux de {name} ?",
        "q_nieces": "Qui sont les nièces de {name} ?",
        "q_children_with_hair": "Quels enfants de {name} ont les cheveux {color} ?",
        "q_children_with_profession": "Quels enfants de {name} travaillent comme {profession} ?",
        "q_siblings_with_profession": "Quels frères ou sœurs de {name} travaillent comme {profession} ?",
        "q_nephews_nieces_with_hair": "Quels neveux ou nièces de {name} ont les cheveux {color} ?",
        "q_uncles_aunts_with_profession": "Quels oncles ou tantes de {name} travaillent comme {profession} ?",
        "q_grandparents_with_hair": "Quels grands-parents de {name} ont les cheveux {color} ?",
        "q_how_many_grandsons": "Combien de petits-fils a {name} ?",
        "q_how_many_granddaughters": "Combien de petites-filles a {name} ?",
        "q_how_many_cousins": "Combien de cousins et cousines a {name} ?",
        "q_parent_with_profession": "Qui a au moins un parent qui travaille comme {profession} ?",
        "q_people_without_parents_profession": "Quelles personnes sans parents travaillent comme {profession} ?",
        
        # Questions multi-hop (raisonnement en chaîne)
        "q_children_of_siblings_of_grandparents": "Qui sont les enfants des frères et sœurs des grands-parents de {name} ?",
        "q_professions_of_in_laws_of_children": "Quelles sont les professions des beaux-parents des enfants de {name} ?",
        "q_same_hair_as_mothers_father": "Qui a la même couleur de cheveux que la mère du père de {name} ?",
        "q_grandchildren_of_siblings": "Qui sont les petits-enfants des frères et sœurs de {name} ?",
        
        # Questions conditionnelles
        "q_if_has_brothers_their_daughters": "Si {name} a des frères, qui sont leurs filles ?",
        "q_children_with_children_same_profession": "Parmi les enfants de {name}, lesquels ont des enfants qui travaillent dans la même profession que {name} ?",
        "q_who_has_more_children": "Qui a plus d'enfants : {name} ou ses frères et sœurs ?",
        "q_if_has_sisters_their_sons": "Si {name} a des sœurs, qui sont leurs fils ?",
        
        # Questions d'exclusion et négation
        "q_who_no_children_with_blue_eyes": "Qui dans la famille n'a PAS d'enfants aux yeux bleus ?",
        "q_generation_not_lawyer_doctor": "Qui de la génération de {name} ne travaille ni comme avocat ni comme médecin ?",
        "q_has_children_no_grandchildren": "Qui a des enfants mais pas de petits-enfants ?",
        "q_no_siblings": "Qui n'a pas de frères et sœurs ?",
        
        # Questions comparatives
        "q_most_descendants": "Qui a le plus grand nombre de descendants dans la famille ?",
        "q_generation_most_blond": "Quelle génération a le plus de personnes aux cheveux blonds ?",
        "q_same_number_children_as": "Qui a autant d'enfants que {name} ?",
        "q_more_grandsons_than_granddaughters": "Qui a plus de petits-fils que de petites-filles ?",
        
        # Questions de chemins relationnels
        "q_relationship_between": "Quel est le lien de parenté entre {name1} et {name2} ?",
        "q_generations_between": "Combien de générations séparent {name1} et {name2} ?",
        "q_common_ancestor": "{name1} et {name2} ont-ils un ancêtre commun ? Si oui, qui ?",
        "q_are_related": "{name1} et {name2} sont-ils apparentés ?",
        
        # Questions énigmes
        "q_enigma_base": "Qui est {relation_chain} ?",
        "the_brother_of": "le frère de",
        "the_sister_of": "la sœur de",
        "the_father_of": "le père de",
        "the_mother_of": "la mère de",
        "the_child_of": "l'enfant de",
        "the_parent_of": "le parent de",
        "the_cousin_of": "le cousin de",
        "the_uncle_of": "l'oncle de",
        "the_aunt_of": "la tante de",
        "the_grandparent_of": "le grand-parent de",
        "the_grandchild_of": "le petit-enfant de",
        "the_son_of": "du fils de",
        "the_daughter_of": "de la fille de",
        "with_hair": "aux cheveux {color}",
        "with_eyes": "aux yeux {color}",
        "working_as": "qui travaille comme {profession}",
        "wearing_hat": "au chapeau {color}",
        
        # Pronoms
        "pronoun_m": "il",
        "pronoun_f": "elle",
        
        # Réponse vide
        "none": "Aucun"
    },
    
    "en": {
        # Templates for text_converter
        "has_hair": "{name} has {hair_color} hair",
        "has_eyes": "{eye_color} eyes",
        "wears_hat": "wears a {hat_color} hat",
        "works_as": "works as a {profession}",
        "has_children_singular": "{name} has 1 child: {children}",
        "has_children_plural": "{name} has {count} children: {children}",
        "is_child_of": "{name} is the child of {parent1} and {parent2}",
        
        # Templates for questions
        "q_children_of": "Who are {name}'s children?",
        "q_parents_of": "Who are {name}'s parents?",
        "q_father_of": "Who is {name}'s father?",
        "q_mother_of": "Who is {name}'s mother?",
        "q_child_of_whom": "Whose child is {name}?",
        "q_parent_of_whom": "Whose parent is {name}?",
        "q_who_works_as": "Who works as a {profession}?",
        "q_who_has_hat": "Who wears a {color} hat?",
        "q_who_has_hair": "Who has {color} hair?",
        "q_who_has_eyes": "Who has {color} eyes?",
        "q_who_has_hair_and_eyes": "Who has {hair} hair and {eyes} eyes?",
        "q_how_many_children": "How many children does {name} have?",
        "q_how_many_with_eyes": "How many people have {color} eyes?",
        "q_how_many_profession": "How many {profession}s are there?",
        "q_siblings_of": "Who are {name}'s siblings?",
        "q_brothers_of": "Who are {name}'s brothers?",
        "q_sisters_of": "Who are {name}'s sisters?",
        "q_grandparents_of": "Who are {name}'s grandparents?",
        "q_grandfathers_of": "Who are {name}'s grandfathers?",
        "q_grandmothers_of": "Who are {name}'s grandmothers?",
        "q_grandchildren_of": "Who are {name}'s grandchildren?",
        "q_grandsons_of": "Who are {name}'s grandsons?",
        "q_granddaughters_of": "Who are {name}'s granddaughters?",
        "q_same_generation_profession": "Who is in the same generation as {name} and works as a {profession}?",
        "q_same_generation_hair": "Who is in the same generation as {name} and has {color} hair?",
        "q_men_same_generation": "Which men are in the same generation as {name}?",
        "q_women_same_generation": "Which women are in the same generation as {name}?",
        "q_oldest_ancestors": "Who are {name}'s oldest ancestors?",
        "q_all_descendants": "Who are all of {name}'s descendants?",
        "q_descendants_profession": "Which descendants of {name} work as a {profession}?",
        "q_people_without_parents": "Who are the people without parents in this tree?",
        "q_people_without_children": "Who are the people without children in this tree?",
        "q_great_grandparents": "Who are {name}'s great-grandparents?",
        "q_great_grandfathers": "Who are {name}'s great-grandfathers?",
        "q_great_grandmothers": "Who are {name}'s great-grandmothers?",
        "q_great_grandchildren": "Who are {name}'s great-grandchildren?",
        "q_great_grandsons": "Who are {name}'s great-grandsons?",
        "q_great_granddaughters": "Who are {name}'s great-granddaughters?",
        "q_uncles_aunts": "Who are {name}'s uncles and aunts?",
        "q_uncles": "Who are {name}'s uncles?",
        "q_aunts": "Who are {name}'s aunts?",
        "q_cousins_all": "Who are {name}'s cousins?",
        "q_cousins_male": "Who are {name}'s male cousins?",
        "q_cousins_female": "Who are {name}'s female cousins?",
        "q_nephews_nieces": "Who are {name}'s nephews and nieces?",
        "q_nephews": "Who are {name}'s nephews?",
        "q_nieces": "Who are {name}'s nieces?",
        "q_children_with_hair": "Which of {name}'s children have {color} hair?",
        "q_children_with_profession": "Which of {name}'s children work as a {profession}?",
        "q_siblings_with_profession": "Which of {name}'s siblings work as a {profession}?",
        "q_nephews_nieces_with_hair": "Which of {name}'s nephews or nieces have {color} hair?",
        "q_uncles_aunts_with_profession": "Which of {name}'s uncles or aunts work as a {profession}?",
        "q_grandparents_with_hair": "Which of {name}'s grandparents have {color} hair?",
        "q_how_many_grandsons": "How many grandsons does {name} have?",
        "q_how_many_granddaughters": "How many granddaughters does {name} have?",
        "q_how_many_cousins": "How many cousins does {name} have?",
        "q_parent_with_profession": "Who has at least one parent who works as a {profession}?",
        "q_people_without_parents_profession": "Which people without parents work as a {profession}?",
        
        # Multi-hop reasoning questions
        "q_children_of_siblings_of_grandparents": "Who are the children of {name}'s grandparents' siblings?",
        "q_professions_of_in_laws_of_children": "What are the professions of {name}'s children's in-laws?",
        "q_same_hair_as_mothers_father": "Who has the same hair color as {name}'s mother's father?",
        "q_grandchildren_of_siblings": "Who are the grandchildren of {name}'s siblings?",
        
        # Conditional questions
        "q_if_has_brothers_their_daughters": "If {name} has brothers, who are their daughters?",
        "q_children_with_children_same_profession": "Which of {name}'s children have children who work in the same profession as {name}?",
        "q_who_has_more_children": "Who has more children: {name} or their siblings?",
        "q_if_has_sisters_their_sons": "If {name} has sisters, who are their sons?",
        
        # Exclusion and negation questions
        "q_who_no_children_with_blue_eyes": "Who in the family does NOT have children with blue eyes?",
        "q_generation_not_lawyer_doctor": "Who in {name}'s generation works neither as a lawyer nor as a doctor?",
        "q_has_children_no_grandchildren": "Who has children but no grandchildren?",
        "q_no_siblings": "Who has no siblings?",
        
        # Comparative questions
        "q_most_descendants": "Who has the most descendants in the family?",
        "q_generation_most_blond": "Which generation has the most people with blond hair?",
        "q_same_number_children_as": "Who has the same number of children as {name}?",
        "q_more_grandsons_than_granddaughters": "Who has more grandsons than granddaughters?",
        
        # Relational path questions
        "q_relationship_between": "What is the relationship between {name1} and {name2}?",
        "q_generations_between": "How many generations separate {name1} and {name2}?",
        "q_common_ancestor": "Do {name1} and {name2} have a common ancestor? If so, who?",
        "q_are_related": "Are {name1} and {name2} related?",
        
        # Riddle questions
        "q_enigma_base": "Who is {relation_chain}?",
        "the_brother_of": "the brother of",
        "the_sister_of": "the sister of",
        "the_father_of": "the father of",
        "the_mother_of": "the mother of",
        "the_child_of": "the child of",
        "the_parent_of": "the parent of",
        "the_cousin_of": "the cousin of",
        "the_uncle_of": "the uncle of",
        "the_aunt_of": "the aunt of",
        "the_grandparent_of": "the grandparent of",
        "the_grandchild_of": "the grandchild of",
        "the_son_of": "the son of",
        "the_daughter_of": "the daughter of",
        "with_hair": "with {color} hair",
        "with_eyes": "with {color} eyes",
        "working_as": "who works as a {profession}",
        "wearing_hat": "wearing a {color} hat",
        
        # Pronouns
        "pronoun_m": "he",
        "pronoun_f": "she",
        
        # Empty response
        "none": "None"
    }
}

def get_translation(key: str, lang: str = "fr") -> str:
    """Récupère une traduction pour une clé donnée."""
    if lang not in TRANSLATIONS:
        lang = "fr"  # Fallback to French
    return TRANSLATIONS[lang].get(key, key)