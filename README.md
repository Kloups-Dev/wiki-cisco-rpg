# Wiki Cisco RPG

Wiki joueur francophone pour **Cisco's Fantasy Medieval RPG [Ultimate] 1.19.2**, construit avec MkDocs Material.

**Wiki en ligne :** https://kloups-dev.github.io/wiki-cisco-rpg/

**Dépôt GitHub :** https://github.com/Kloups-Dev/wiki-cisco-rpg

Le projet indexe les objets, recettes, équipements, sorts, gemmes, améliorations, boss et dimensions qui interagissent réellement avec le joueur.

## Voir le wiki sur son PC

Avec Python installé, ouvrir un terminal dans ce dossier puis lancer :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
mkdocs serve
```

Ouvrir ensuite l'adresse affichée, normalement `http://127.0.0.1:8000/`.

## Vérifier la construction

```powershell
mkdocs build --strict
```

Le site généré apparaît dans `site/`, dossier volontairement ignoré par Git.

## Publier sur GitHub Pages

1. Créer le dépôt `Kloups-Dev/wiki-cisco-rpg`.
2. Faire le premier commit puis pousser la branche `main`.
3. Sur GitHub, ouvrir **Settings → Pages**.
4. Dans **Build and deployment → Source**, choisir **GitHub Actions**.
5. Ouvrir l'onglet **Actions** et attendre la fin du workflow « Déployer le wiki ».

L'URL attendue est `https://kloups-dev.github.io/wiki-cisco-rpg/`.

## Régénérer le catalogue joueur

Le générateur sélectionne les familles de mods décrites dans `data/content-groups.json`, lit les traductions, modèles, textures et recettes, puis applique les personnalisations CraftTweaker de Cisco. Il produit les fiches d'objets, les grilles façon JEI et les index par thème.

Exemple pour l'instance Prism Launcher :

```powershell
python tools/generate_player_catalog.py "C:\chemin\vers\minecraft\mods" `
  --minecraft-jar "C:\chemin\vers\minecraft-1.19.2-client.jar" `
  --crafttweaker-script "C:\chemin\vers\minecraft\scripts\Cisco.zs"
```

Le dernier passage a indexé **26 familles**, **4 666 objets et blocs**, **4 106 recettes** et **13 recettes CraftTweaker**.

