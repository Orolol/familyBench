"""Module de visualisation des arbres généalogiques."""

from typing import Dict
from tree_evaluator.models import Person

def visualize_tree(people: Dict[str, Person], output_path: str = "family_tree"):
    """Génère une visualisation de l'arbre généalogique.

    Nécessite le paquet optionnel `graphviz` (pip install graphviz) ainsi que
    le binaire Graphviz (`dot`) sur la machine.
    """
    try:
        import graphviz
    except ImportError as e:
        raise ImportError(
            "The optional dependency 'graphviz' is required for --visualize. "
            "Install it with `pip install graphviz` (and the Graphviz binaries)."
        ) from e

    dot = graphviz.Digraph(comment='Family Tree', format='png')
    dot.attr(rankdir='TB')
    
    # Ajouter les nœuds (personnes)
    for pid, person in people.items():
        # Couleur différente selon le genre
        color = "lightblue" if person.gender == "M" else "pink"
        
        label = f"{person.first_name}\n({person.profession})"
        dot.node(pid, label, style="filled", fillcolor=color, shape="box" if person.gender == "M" else "ellipse")
        
    # Ajouter les arêtes (relations)
    # Pour éviter les doublons, on trace uniquement parents -> enfants
    for pid, person in people.items():
        for child_id in person.children_ids:
            if child_id in people:
                dot.edge(pid, child_id)
                
    # Sauvegarder
    try:
        output_file = dot.render(output_path, cleanup=True)
        print(f"Visualisation sauvegardée dans : {output_file}")
        return output_file
    except Exception as e:
        print(f"Erreur lors de la génération de la visualisation : {e}")
        return None
