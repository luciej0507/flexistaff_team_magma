# Pour le lead : découper les `Cellule` de Magma (section 3.4 ter)

Ce que j'ai écrit et testé dans ma copie de `parsing_jour3.ipynb`. À coller dans le notebook commun.

## Ce que ça fait

Une `Cellule` de Magma a deux formes :

- **grille de mois** : la case entière du jour ; 1re ligne = numéro du jour, puis une ligne par événement ;
- **planning hebdo** : un seul créneau (horaire, puis lieu) ; la date vient de la colonne (`associer`).

`decouper_cellule(zone)` renvoie `(numero_du_jour, [textes d'événements])` :

| Case lue par l'OCR | Résultat |
|---|---|
| `27` / `9h15 Atelier` | `(27, ['9h15 Atelier'])` |
| `23` | `(23, [])` : jour vide, pas d'événement |
| `9h à 18h` / `Hangar C` | `(None, ['9h à 18h Hangar C'])` : planning hebdo |
| rien | `(None, [])` : pas d'événement vide |

Elle utilise le champ `lignes` du JSON, ajouté par l'intervenant dans `test_ocr_champion.ipynb` le 18/11.
**Le `ocr_champion.json` doit donc être produit avec cette version** (avec un ancien JSON, la fonction marche
mais ne découpe rien).

Testée sur `ocr_champion.json` (champion v8) : 110 cases de mois (dont 68 vides) et 108 cellules hebdo reconnues.

## 1. Section 3 : une cellule de code, juste après `associer` / `associer_ligne`

```python
def textes_des_lignes(zone):
    """Renvoie la liste des textes des lignes de la zone, de haut en bas.

    >>> textes_des_lignes({"texte": "27 9h15 Atelier", "lignes": [{"texte": "27"}, {"texte": "9h15 Atelier"}]})
    ['27', '9h15 Atelier']
    >>> textes_des_lignes({"texte": "9h à 18h Quai B"})      # ancien JSON, sans « lignes »
    ['9h à 18h Quai B']
    >>> textes_des_lignes({"texte": "", "lignes": []})      # l'OCR n'a rien lu
    []
    """
    textes = []
    for ligne in zone.get("lignes", []):  # .get(..., []) : liste vide si la clé « lignes » n'existe pas
        texte = ligne["texte"].strip()
        if texte != "":
            textes.append(texte)
    # Un JSON produit avant le 18/11 n'a pas de « lignes » : on garde alors le texte entier, en une seule ligne
    if len(textes) == 0 and zone["texte"].strip() != "":
        textes = [zone["texte"].strip()]
    return textes


def decouper_cellule(zone):
    """Découpe une Cellule de Magma en (numéro du jour, liste des textes d'événements).

    - Grille de mois : la première ligne commence par le numéro du jour, puis chaque ligne est un événement.
    - Planning hebdo : pas de numéro ; toute la case est UN seul événement (l'horaire, puis le lieu).

    >>> decouper_cellule({"texte": "", "lignes": [{"texte": "27"}, {"texte": "9h15 Atelier"}]})
    (27, ['9h15 Atelier'])
    >>> decouper_cellule({"texte": "", "lignes": [{"texte": "16 10:15 Coiffeur"}, {"texte": "18:00 Cinéma"}]})
    (16, ['10:15 Coiffeur', '18:00 Cinéma'])
    >>> decouper_cellule({"texte": "", "lignes": [{"texte": "23"}]})
    (23, [])
    >>> decouper_cellule({"texte": "", "lignes": [{"texte": "9h à 18h"}, {"texte": "Hangar C"}]})
    (None, ['9h à 18h Hangar C'])
    >>> decouper_cellule({"texte": "09:00 à 18.00 Chantier A7"})
    (None, ['09:00 à 18.00 Chantier A7'])
    >>> decouper_cellule({"texte": "", "lignes": []})       # case où l'OCR n'a rien lu
    (None, [])
    """
    lignes = textes_des_lignes(zone)
    if len(lignes) == 0:
        return None, []  # l'OCR n'a rien lu dans la case : pas d'événement (et surtout pas un événement vide)

    mots = lignes[0].split()  # les mots de la première ligne

    # Le numéro du jour est le premier mot, s'il ne contient que 1 ou 2 chiffres :
    # « 27 » oui ; « 9h », « 09:00 » ou « 0900 » non (ce sont des heures).
    if len(mots) > 0 and mots[0].isdigit() and len(mots[0]) <= 2:
        numero = int(mots[0])
        evenements = []

        # Le reste de la première ligne : le 1er événement, si l'OCR l'a lu sur la même ligne que le numéro
        reste = " ".join(mots[1:])
        if reste != "":
            evenements.append(reste)

        # Chacune des lignes suivantes est un événement
        for ligne in lignes[1:]:
            evenements.append(ligne)

        return numero, evenements  # liste vide : jour sans événement

    # Pas de numéro : planning hebdo, toute la case est un seul événement
    return None, [" ".join(lignes)]
```

## 2. Section 4 : le test

À ajouter avant la boucle `for nom, f in [...]` :

```python
def test_decouper_cellule():
    """Magma : une case de mois donne son numéro et un événement par ligne ; une cellule hebdo reste entière."""
    assert decouper_cellule({"texte": "", "lignes": [{"texte": "27"}, {"texte": "9h15 Atelier"}]}) == (27, ["9h15 Atelier"])
    assert decouper_cellule({"texte": "", "lignes": [{"texte": "16 10:15 Coiffeur"}, {"texte": "18:00 Cinéma"}]}) \
        == (16, ["10:15 Coiffeur", "18:00 Cinéma"])
    assert decouper_cellule({"texte": "", "lignes": [{"texte": "23"}]}) == (23, [])  # jour vide
    assert decouper_cellule({"texte": "", "lignes": [{"texte": "9h à 18h"}, {"texte": "Hangar C"}]}) \
        == (None, ["9h à 18h Hangar C"])
    assert decouper_cellule({"texte": "09:00 à 18.00 Chantier A7"}) == (None, ["09:00 à 18.00 Chantier A7"])  # sans lignes
    assert decouper_cellule({"texte": "", "lignes": []}) == (None, [])  # rien lu : pas d'événement vide
```

Et dans la liste de la boucle, ajouter : `("decouper_cellule", test_decouper_cellule)`.

## 3. Section 3.6 : dans `parser()`, pour chaque `Cellule`

```python
numero, textes_evenements = decouper_cellule(zone)
for texte_evt in textes_evenements:          # un événement par morceau
    texte_propre = normaliser(texte_evt)
    debut, fin = extraire_heures(texte_propre)
    if numero is not None:
        # grille de mois : la date vient du numéro de la case et du mois lu dans le Titre (extraire_mois_annee)
        date = extraire_date(str(numero), annee=annee, mois=mois)
    else:
        # planning hebdo : la date vient de la zone Date de la même colonne (associer)
        date = ...
    # puis : titre (texte sans les heures), confiance(...), evenements.append({...})
```

## 4. Section 3 : les classes de Magma

```python
CLASSES_EVENEMENT = {"Cellule", "Cellule_code"}
CLASSES_DATE = {"Date"}
CLASSES_ENTETE_MOIS = {"Titre"}
CLASSES_PERSONNE = {"Nom"}
```

## À savoir

- Une ligne sans heure (`Ateller`, `Inventaire`) devient un événement **sans heure** : `confiance` doit le mettre
  « à vérifier ».
- Une ligne avec seulement une heure (`12h45`) : l'OCR a perdu le titre ; à mettre aussi « à vérifier ».
- Les événements d'une case suivent l'ordre des lignes, pas l'ordre des heures.
