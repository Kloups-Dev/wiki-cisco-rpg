---
search:
  exclude: true
---

# Rangement et coffres

!!! success "Vérifié — métadonnées des mods installés"
    Cette page s'appuie sur les descriptions embarquées dans les `.jar` présents dans l'instance.

## Le plus simple : Tom's Simple Storage

**Tom's Simple Storage** (`toms_storage-1.19-1.5.11.jar`) est le mod de stockage centralisé du pack. Ses métadonnées le décrivent comme un système de stockage simple, dans le style vanilla.

Pour préparer un réseau sans deviner les recettes :

1. ouvre JEI et cherche `@toms_storage` ;
2. repère les éléments contenant `Connector`, `Terminal`, `Cable` ou `Inventory` ;
3. consulte dans JEI leur recette et leurs usages pour cette version du pack.

<div class="object-gallery" markdown>

<div class="object-card" markdown>
![Connecteur d'inventaire Tom's Storage](../assets/images/items/toms-storage-inventory-connector.png){ .item-icon }

**Inventory Connector**

Le point de départ du réseau.
</div>

<div class="object-card" markdown>
![Terminal Tom's Storage](../assets/images/items/toms-storage-terminal.png){ .item-icon }

**Storage Terminal**

La face du bloc depuis lequel on consulte le stockage.
</div>

<div class="object-card" markdown>
![Câble d'inventaire Tom's Storage](../assets/images/items/toms-storage-inventory-cable.png){ .item-icon }

**Inventory Cable**

Le câble qui relie les éléments du réseau.
</div>

</div>

<p class="image-credit">Textures exactes de Tom's Simple Storage 1.5.11. Les noms restent en anglais pour les retrouver sans ambiguïté dans JEI.</p>

!!! note "Pourquoi pas une recette copiée ici ?"
    KubeJS et CraftTweaker sont installés et peuvent modifier les recettes. JEI affiche la recette réellement chargée par votre partie.

## Les autres solutions présentes

- **Storage Drawers** : blocs à tiroirs prévus pour stocker et récupérer rapidement des objets, particulièrement pratiques pour les ressources en grande quantité.
- **Sophisticated Backpacks** : sacs à dos fonctionnels. `Sophisticated Core` est également présent, sa dépendance obligatoire.
- **Iron Chests** : variantes de coffres de plus grande capacité.
- **Carry On** : mod présent dans l'instance ; sa fiche d'utilisation précise reste à compléter.
- **Quark** : mod présent ; ses fonctions actives dépendent de sa configuration et ne sont pas toutes documentées ici.

## Organisation conseillée

- Garde les objets courants dans le réseau Tom's Storage.
- Réserve les Storage Drawers aux blocs et ressources accumulés en masse.
- Utilise les sacs à dos pour l'exploration, sans y mettre l'unique exemplaire d'un objet critique tant que tu ne connais pas le comportement en cas de mort.

