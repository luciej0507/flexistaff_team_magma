"""Entraîne un modèle YOLO sur le dataset de plannings, sur le GPU du Mac, et trace tout dans MLflow.

Ce qui part dans MLflow : les paramètres (modèle, epochs, taille d'image, nombre d'images réelles et
synthétiques), les métriques (mAP50, précision, rappel), le fichier best.pt et l'export ONNX que
charge l'application.

Utilisation (depuis la racine du dépôt) :
    .venv/bin/python ai_training/train.py --creds ~/Downloads/identifiants-<login>.json --run-name <prénom>_v1

Le fichier d'identifiants reste hors du dépôt : il contient des mots de passe.

Sans la VM (serveur éteint, pas de réseau), l'option --local range le run sur le Mac,
dans le dossier mlruns/ (ignoré par git), au lieu du serveur de la formation :
    .venv/bin/python ai_training/train.py --local --run-name <prénom>_essai
Ces runs locaux ne sont pas visibles par l'équipe : ils servent à vérifier que tout marche.
"""

import argparse
import json
import os
from pathlib import Path

import mlflow
import onnx
from ultralytics import YOLO, settings

SQUAD = "team-magma"
DEFAULT_DATA = "dataset/team_magma_lot_corrige/data.yaml"
DEVICE = "mps"  # "mps" = le GPU des puces Apple (M1 à M5)
LOCAL_DIR = "mlruns"  # dossier des runs locaux (option --local), exclu par le .gitignore
SYNTH_PREFIX = "synth_"  # les images du générateur s'appellent synth_0000.jpg, synth_0001.jpg…
# Chemin absolu du dossier runs/ du dépôt. Piège : avec un chemin relatif ("runs"), Ultralytics
# le range sous son propre dossier de résultats, et on obtient runs/detect/runs/<nom du run>.
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def parse_args() -> argparse.Namespace:
    """Lit les options de la ligne de commande : identifiants, nom du run, données et réglages."""
    parser = argparse.ArgumentParser(description="Entraînement YOLO tracé dans MLflow")
    parser.add_argument("--creds", help="chemin du fichier identifiants-<login>.json (serveur de la formation)")
    parser.add_argument("--local", action="store_true", help="ranger le run sur le Mac, sans la VM")
    parser.add_argument("--run-name", required=True, help="nom du run, ex. nathalie_v1")
    parser.add_argument("--data", default=DEFAULT_DATA, help="chemin du data.yaml du dataset")
    parser.add_argument("--model", default="yolov8s", help="modèle de départ (yolov8s, yolo26s…)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--dataset-version", required=True, help="version du dataset, notée en tag (ex. v1, v2)")
    args = parser.parse_args()
    # Il faut savoir où ranger le run : sur le serveur (--creds) ou sur le Mac (--local).
    if not args.local and not args.creds:
        parser.error("indiquez --creds <fichier> (serveur de la formation) ou --local (sur le Mac)")
    return args


def connect_mlflow(creds_path: str) -> None:
    """Se connecte au serveur MLflow de la formation avec les identifiants du portail."""
    creds = json.load(open(os.path.expanduser(creds_path)))["mlflow"]
    os.environ["MLFLOW_TRACKING_USERNAME"] = creds["username"]
    os.environ["MLFLOW_TRACKING_PASSWORD"] = creds["password"]
    mlflow.set_tracking_uri(creds["tracking_uri"])
    mlflow.set_experiment(f"flexistaff_{SQUAD}")


def connect_local_mlflow() -> None:
    """Range les runs sur le Mac : une petite base SQLite et les fichiers, tout dans mlruns/."""
    os.makedirs(LOCAL_DIR, exist_ok=True)  # SQLite ne crée pas le dossier tout seul
    mlflow.set_tracking_uri(f"sqlite:///{LOCAL_DIR}/mlflow.db")
    mlflow.set_experiment(f"flexistaff_{SQUAD}")


def count_train_images(data_yaml: str) -> dict:
    """Compte les images d'entraînement réelles (CVAT) et synthétiques (générateur), pour MLflow."""
    train_dir = Path(data_yaml).parent / "images" / "train"
    images = [p for p in train_dir.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    n_synth = sum(p.name.startswith(SYNTH_PREFIX) for p in images)
    return {"n_images_cvat": len(images) - n_synth, "n_images_synth": n_synth}


def check_onnx_output(onnx_model: onnx.ModelProto, n_classes: int) -> None:
    """Vérifie que la sortie ONNX a la forme lue par l'application : [1, 4 + nb_classes, N].

    Piège : YOLO26 (ou YOLOv10) exporté « sans NMS » sort [1, 300, 6], que CalEvent ne sait pas lire.
    On s'arrête alors AVANT d'enregistrer le modèle, pour ne pas ranger dans MLflow un ONNX inutilisable.
    """
    dims = onnx_model.graph.output[0].type.tensor_type.shape.dim
    shape = [d.dim_value or d.dim_param for d in dims]
    expected = 4 + n_classes
    if len(shape) != 3 or shape[1] != expected:
        raise SystemExit(f"Sortie ONNX {shape} : l'application attend [1, {expected}, N]. Modèle non enregistré.")
    print(f"Sortie ONNX {shape} : format compatible avec l'application.")


def train_and_log(args: argparse.Namespace) -> None:
    """Entraîne le modèle dans un run MLflow, puis y range les métriques, best.pt et l'export ONNX."""
    # Le suivi MLflow est fait à la main ci-dessous. On coupe celui intégré à Ultralytics, qui sinon
    # relogue ses propres paramètres dans le même run (conflit). C'est aussi ce que fait le notebook officiel.
    settings.update({"mlflow": False})
    model = YOLO(f"{args.model}.pt")  # poids pré-entraînés téléchargés au premier lancement

    with mlflow.start_run(run_name=args.run_name):
        mlflow.set_tags({"squad": SQUAD, "dataset": args.dataset_version, "device": DEVICE})
        mlflow.log_params({"model": args.model, "epochs": args.epochs, "imgsz": args.imgsz,
                           **count_train_images(args.data)})

        # project/name : les résultats bruts de YOLO vont dans runs/<nom du run>, facile à retrouver
        results = model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, device=DEVICE,
                              project=str(RUNS_DIR), name=args.run_name)
        mlflow.log_metrics({
            "mAP50": results.box.map50,
            "precision": results.box.mp,
            "recall": results.box.mr,
        })

        best_pt = model.trainer.best  # runs/<nom du run>/weights/best.pt
        mlflow.log_artifact(str(best_pt))
        mlflow.log_artifact(str(Path(model.trainer.save_dir) / "results.png"))  # courbes d'entraînement

        # Export ONNX, vérifié puis rangé dans le run : c'est le format que charge l'application.
        # Pas d'option end2end ni nms : sinon la sortie change de forme (voir check_onnx_output).
        onnx_model = onnx.load(YOLO(best_pt).export(format="onnx", imgsz=args.imgsz))
        check_onnx_output(onnx_model, len(model.names))
        mlflow.onnx.log_model(onnx_model, name="onnx", save_as_external_data=False)


def main() -> None:
    """Point d'entrée : lit les options, se connecte à MLflow et lance l'entraînement."""
    args = parse_args()
    if args.local:
        connect_local_mlflow()
    else:
        connect_mlflow(args.creds)
    train_and_log(args)


if __name__ == "__main__":
    main()
