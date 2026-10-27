# Fiabilité du wiki

Le wiki indique clairement ce qui vient des fichiers du pack et ce qui demande encore un test réel en jeu.

## Ce qui est vérifié automatiquement

- la présence et la version des fichiers `.jar` ;
- les noms français et anglais fournis par les mods ;
- les modèles et textures d'objets de cette installation ;
- les recettes JSON incluses dans les mods sélectionnés ;
- les recettes remplacées ou ajoutées par `scripts/Cisco.zs` avec CraftTweaker ;
- les liens entre un ingrédient et les recettes qui l'utilisent.

## Ce qui reste à vérifier en jeu

- les statistiques calculées dynamiquement : dégâts, mana, affixes, châsses et NBT ;
- les butins aléatoires de coffres, mobs et boss ;
- les commandes exactes et touches configurées par le joueur ;
- les recettes ajoutées à l'exécution par du code Java ;
- les changements propres au serveur qui ne figurent pas dans l'instance locale.

Une fiche sans recette directe ne signifie donc pas que l'objet est impossible à obtenir : il peut être du butin, une récompense, un échange ou le résultat d'une mécanique spéciale.

## Ordre de priorité des sources

1. **Fichiers exacts de l'instance Cisco 1.19.2** : ils décident des objets et recettes affichés.
2. **Personnalisation Cisco** : CraftTweaker remplace la recette originale lorsqu'il la modifie.
3. **Wiki ou documentation officielle du mod** : utilisé pour expliquer le fonctionnement général.
4. **Test réel en jeu et JEI** : nécessaire pour valider les valeurs dynamiques et le comportement du serveur.

## Images

L'illustration de l'accueil a été créée pour ce wiki. Les icônes pixelisées sont extraites des ressources des mods installés et servent uniquement à reconnaître les objets ; elles restent la propriété de leurs auteurs respectifs.

## Corriger ou enrichir une fiche

Pour ajouter une information fiable, joindre si possible le nom de l'objet, le mod affiché dans l'infobulle, la recette JEI, la version du mod et une capture ou un test reproductible.

