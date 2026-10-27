# Recettes et infobulles

Chaque fiche d'objet essaie de reproduire l'essentiel de l'expérience JEI sans lancer Minecraft.

## Ce qu'une fiche affiche

- l'icône exacte fournie par le mod installé ;
- le nom traduit, son nom anglais lorsqu'il diffère, le mod et l'identifiant technique ;
- les recettes de fabrication, forge, taille de pierre et machines reconnues ;
- les objets fabriqués avec cet ingrédient ;
- le fichier source de chaque recette.

## Recettes Cisco prioritaires

Le script `scripts/Cisco.zs` retire certaines recettes d'origine et en ajoute de nouvelles. Le générateur lit ce fichier après les recettes des mods : les treize recettes Cisco détectées sont donc affichées comme source CraftTweaker et remplacent les versions supprimées.

!!! warning "JEI reste l'arbitre en jeu"
    Certaines recettes sont créées par du code, dépendent d'un tag dont le contenu varie, ou ne sont disponibles que dans des conditions précises. En cas d'écart, la recette visible dans JEI sur le serveur est la référence finale.

## Lire la grille

- Une case illustrée représente un objet précis.
- Une case marquée `#` représente un tag accepté par la recette : plusieurs objets peuvent convenir.
- Le nombre sur le résultat indique la quantité obtenue.
- Le type de recette et son identifiant sont affichés au-dessus de la grille.

[Ouvrir le catalogue →](catalogue/index.md)
