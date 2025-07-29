# Spécification - Outil d'évaluation LLM par arbres généalogiques aléatoires

## Vue d'ensemble

Création d'un benchmark dynamique pour évaluer les capacités de raisonnement relationnel des LLMs en générant des arbres généalogiques aléatoires, leur description textuelle et des questions-réponses associées.

## Architecture du système

### 1. Génération de l'arbre généalogique

#### Structure de données
```python
class Person:
    - id: str (unique)
    - first_name: str (unique)
    - profession: str (unique)
    - hair_color: str
    - eye_color: str
    - hat_color: str
    - parent_ids: List[str]
    - children_ids: List[str]
    - generation: int
```

#### Paramètres configurables
- `max_depth`: Profondeur maximale de l'arbre (nombre de générations)
- `total_people`: Nombre total de personnes à générer
- `max_children_per_person`: Nombre maximum d'enfants par personne
- `seed`: Graine pour la reproductibilité (optionnel)

#### Contraintes
- Chaque personne a un prénom unique
- Chaque personne a une profession unique
- La combinaison (couleur_cheveux, couleur_yeux, couleur_chapeau) est unique
- Structure d'arbre simple : pas de remariages, chaque enfant a exactement 2 parents

#### Listes d'attributs
- **Prénoms** : Liste suffisamment large pour garantir l'unicité
- **Professions** : médecin, ingénieur, professeur, artiste, boulanger, etc.
- **Couleurs cheveux** : blond, brun, roux, noir, gris
- **Couleurs yeux** : bleu, vert, marron, gris, noir
- **Couleurs chapeau** : rouge, bleu, vert, jaune, noir, blanc, violet

### 2. Conversion en texte

#### Format de description
La description suit un format structuré et prévisible :
```
[Prénom] a les cheveux [couleur], les yeux [couleur], porte un chapeau [couleur] et travaille comme [profession].
[Prénom] est l'enfant de [Parent1] et [Parent2].
[Prénom] a [nombre] enfant(s) : [Liste des enfants].
```

#### Ordre de présentation
- Parcours en largeur (BFS) de l'arbre, génération par génération
- Au sein d'une génération, ordre alphabétique des prénoms

### 3. Génération des questions

#### Types de questions

**1. Relations directes**
- "Qui est le père/la mère de [Prénom] ?"
- "Qui sont les enfants de [Prénom] ?"
- "Qui sont les parents de [Prénom] ?"

**2. Relations inverses**
- "De qui [Prénom] est-il/elle l'enfant ?"
- "De qui [Prénom] est-il/elle le parent ?"

**3. Recherche par attributs**
- "Qui a les cheveux [couleur] ?"
- "Qui travaille comme [profession] ?"
- "Qui porte un chapeau [couleur] ?"

**4. Recherche multi-critères**
- "Qui a les cheveux [couleur] et les yeux [couleur] ?"
- "Qui est [profession] et a des enfants aux cheveux [couleur] ?"
- "Qui porte un chapeau [couleur] et est parent de [Prénom] ?"

**5. Questions de comptage**
- "Combien d'enfants a [Prénom] ?"
- "Combien de personnes ont les yeux [couleur] ?"
- "Combien de [profession] y a-t-il ?"

**6. Relations complexes**
- "Qui sont les frères et sœurs de [Prénom] ?"
- "Qui sont les grands-parents de [Prénom] ?"
- "Qui sont les petits-enfants de [Prénom] ?"
- "Qui sont les oncles/tantes de [Prénom] ?"

#### Format des réponses
- **Nom unique** : "Jean"
- **Liste de noms** : "Marie,Paul,Sophie" (ordre alphabétique, séparés par des virgules)
- **Nombre** : "3"
- **Aucun** : "Aucun" (si aucune personne ne correspond)

### 4. Structure du benchmark

#### Fichier de sortie
```json
{
    "tree_description": "Description textuelle complète de l'arbre",
    "prompt_template": "Tu es un assistant qui doit répondre à des questions...",
    "questions": [
        {
            "id": 1,
            "question": "Qui est le père de Marie ?",
            "answer": "Jean",
            "type": "relation_directe"
        }
    ],
    "metadata": {
        "total_people": 50,
        "tree_depth": 4,
        "seed": 12345,
        "generation_timestamp": "2024-01-15T10:30:00Z"
    }
}
```

### 5. Évaluation

#### Métriques
- **Accuracy** : Pourcentage de réponses exactes (exact match)
- **Accuracy par type** : Accuracy pour chaque type de question
- **Taux d'hallucination** : Pourcentage de réponses contenant des prénoms inventés

#### Validation des réponses
- Normalisation : suppression des espaces, mise en minuscules
- Pour les listes : vérification de l'ordre alphabétique et de la complétude
- Détection des hallucinations : vérifier que tous les prénoms existent dans l'arbre

### 6. Interface CLI

```bash
# Génération d'un benchmark
python generate_benchmark.py --depth 4 --people 50 --questions 100 --output benchmark.json

# Évaluation d'un modèle
python evaluate.py --benchmark benchmark.json --model gpt-4 --output results.json

# Analyse des résultats
python analyze_results.py --results results.json
```

### 7. Considérations techniques

#### Performance
- Utilisation de dictionnaires pour les recherches O(1)
- Pré-calcul des relations (frères/sœurs, grands-parents) lors de la génération

#### Validation
- Vérification de la cohérence de l'arbre (pas de cycles, relations bidirectionnelles)
- Vérification de l'unicité des contraintes
- Test que toutes les questions ont une réponse valide

#### Extensibilité
- Architecture modulaire permettant l'ajout de nouveaux types de questions
- Possibilité d'ajouter de nouveaux attributs
- Support pour différents formats de sortie

## Exemples

### Exemple d'arbre minimal
```
Alice a les cheveux blonds, les yeux bleus, porte un chapeau rouge et travaille comme médecin.
Bob a les cheveux bruns, les yeux verts, porte un chapeau bleu et travaille comme ingénieur.
Alice et Bob ont 2 enfants : Charlie, Diana.
Charlie a les cheveux blonds, les yeux verts, porte un chapeau jaune et travaille comme professeur.
Diana a les cheveux roux, les yeux bleus, porte un chapeau vert et travaille comme artiste.
```

### Exemples de questions
1. "Qui sont les enfants d'Alice ?" → "Charlie,Diana"
2. "Qui a les cheveux blonds et les yeux verts ?" → "Charlie"
3. "Combien d'enfants ont Alice et Bob ?" → "2"
4. "Qui travaille comme médecin ?" → "Alice"

## Prochaines étapes

1. Validation de la spécification
2. Implémentation du générateur d'arbres
3. Implémentation du convertisseur texte
4. Implémentation du générateur de questions
5. Tests unitaires et d'intégration
6. Documentation utilisateur
7. Benchmarks de référence sur plusieurs LLMs