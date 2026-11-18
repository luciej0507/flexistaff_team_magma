"""Sépare le dataset exporté de CVAT en deux lots : entraînement (train) et validation (val).

Pourquoi : YOLO doit mesurer ses progrès (mAP, rappel) sur des images qu'il n'a jamais vues
pendant l'apprentissage. On met donc environ 20 % des images de côté dans `val`.

Le script déplace chaque image ET son fichier de labels (même nom, extension .txt),
puis réécrit `data.yaml` pour pointer vers les deux dossiers.

Utilisation :
    python ai_training/split_dataset.py dataset/team_magma
"""

import random
import shutil
import sys
from pathlib import Path

VAL_RATIO = 0.2  # part des images envoyées en validation
SEED = 42  # graine fixe : le même découpage à chaque lancement, donc des runs comparables

CLASS_NAMES = ["Date", "Cellule", "Nom", "Titre", "Cellule_code"]  # ordre de l'export CVAT


def find_train_images(dataset_dir: Path) -> list[Path]:
    """Liste toutes les images du dossier images/train, sous-dossiers compris."""
    train_dir = dataset_dir / "images" / "train"
    return sorted(p for p in train_dir.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def label_path_for(image_path: Path) -> Path:
    """Donne le chemin du fichier de labels d'une image : /images/ devient /labels/, .jpg devient .txt."""
    parts = ["labels" if part == "images" else part for part in image_path.parts]
    return Path(*parts).with_suffix(".txt")


def move_to_val(image_path: Path) -> None:
    """Déplace une image et son label de train vers val, en gardant les sous-dossiers."""
    for source in (image_path, label_path_for(image_path)):
        target = Path(*["val" if part == "train" else part for part in source.parts])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))


def write_data_yaml(dataset_dir: Path) -> None:
    """Réécrit data.yaml avec le chemin absolu du dataset et les dossiers train / val."""
    lines = [
        f"path: {dataset_dir.resolve()}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    lines += [f"  {index}: {name}" for index, name in enumerate(CLASS_NAMES)]
    (dataset_dir / "data.yaml").write_text("\n".join(lines) + "\n")


def main() -> None:
    """Tire au hasard les images de validation, les déplace, puis met à jour data.yaml."""
    dataset_dir = Path(sys.argv[1])
    if (dataset_dir / "images" / "val").exists():
        sys.exit("Le dossier images/val existe déjà : le découpage a déjà été fait.")

    images = find_train_images(dataset_dir)
    random.Random(SEED).shuffle(images)
    val_count = round(len(images) * VAL_RATIO)

    for image_path in images[:val_count]:
        move_to_val(image_path)
    write_data_yaml(dataset_dir)

    print(f"{len(images) - val_count} images en train, {val_count} en val. data.yaml mis à jour.")


if __name__ == "__main__":
    main()
