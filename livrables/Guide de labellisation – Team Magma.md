# Guide de labellisation – Plannings

Nov 16, 2026 - Team Magma

## 1. Objectif

Sophie, à l'accueil, reçoit chaque semaine de nouveaux plannings. Elle a besoin d'un système fiable pour les centraliser dans un calendrier unique, avec les horaires de chaque personne. Ce guide fixe les règles d'annotation des images de plannings pour que tous les annotateurs produisent les mêmes boîtes.

## 2. Données

Le jeu de données compte 40 images de plannings (calendriers).
Les images ont été annotées avec l'outil CVAT. Le format d'export est Ultralytics YOLO Detection 1.0.

## 3. Classes

Cinq classes sont utilisées. Les noms ci-dessous sont les noms exacts des labels.

| Label | Ce qu'il désigne | Exemple |
| --- | --- | --- |
| `Titre` | Titre du planning | Novembre 2025 |
| `Nom` | Nom de la personne ou métier | Mr. Durant, coiffeur |
| `Date` | En-têtes de jours et de dates | Lun 2, 04/06 |
| `Cellule` | Cellule de travail : horaire, événement ou n° jour | 14h/22h entrepot nord |
| `cellule_code` | Cellule de travail contenant un code | J09, RH |

### Pourquoi ces labels

- Ils regroupent les informations dont on a besoin. Grâce au parsing, on arrivera à sortir des informations propre.

### Ce qu'on a écarté

- Jours de la semaine : informations trouvables grâce à la date.
- case vides : pas d'infos pertinantes.
- légendes (info complémentaires).

## 4. Règles générales de tracé

- **Rectangles uniquement**, alignés sur les axes de l'image. Pas de polygones.
- **Suivre le tracé du tableau** : la boîte reprend au maximum la forme de la case du calendrier.
- **Image inclinée** : suivre au maximum le tracé du tableau, en gardant des rectangles droits
- **Image floue** : annoter si un humain reconnaît l'objet et sa classe. Sinon, ne pas annoter.

## 5. Règles par classe

| Label | Contenu | Règle |
| --- | --- | --- |
| `Date` | Jour | Prendre le nombre en entier |
| `Date` | Mois | Texte du mois en entier (« Novembre », pas « nov ») |
| `Date` | Jour/Mois | Paire jour/mois en chiffres |
| `Date` | Jour de la semaine + date | Une seule boîte sur tout l'en-tête (« Lun 2 », pas seulement « 2 ») |
| `Cellule` | Heure | Soit une heure seule, soit une plage heure de début / heure de fin (14:00, 14h/22h) |
| `cellule_code` | Code horaire | Format spécifique à l'EHPAD (J09, RH) |
| `Nom` | Personne | Nom complet + prénom ou genre |
| `Nom` | Poste | Intitulé du poste (coiffeur) |

### 6. Cas limites

- Case contenant seulement un tiret, une croix ou des hachures : elle compte comme vide, on ne l'annote pas.
- Autres cas : à compléter au fil de l'annotation.

## 7. Ce qu'on n'annote pas

- Les éléments flous qu'un humain ne reconnaît pas (voir règle générale).
- Les cases vides : pas d'information pertinente.
- Les légendes (informations complémentaires).
- Les jours de la semaine seuls. Accolés à une date, ils entrent dans la boîte `Date` (voir §5).

## 8. Contrôle qualité

Un contrôle croisé est envisagé. Modalités à définir :

- 4 annotateurs 10 images/personne.
- Le chef tranche en cas de désaccord.
