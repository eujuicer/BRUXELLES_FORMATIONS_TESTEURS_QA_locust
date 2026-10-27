import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _obligatoire(nom):
    valeur = os.getenv(nom)
    if not valeur:
        raise RuntimeError(f"Variable {nom} manquante : copiez .env.example en .env et remplissez-la")
    return valeur


HOST = os.getenv("EVENTFLOW_HOST", "http://localhost:8000")

CLIENT_EMAIL = _obligatoire("CLIENT_EMAIL")
CLIENT_PASSWORD = _obligatoire("CLIENT_PASSWORD")

ORGA_EMAIL = _obligatoire("ORGA_EMAIL")
ORGA_PASSWORD = _obligatoire("ORGA_PASSWORD")

SEUIL_P95_MS = float(os.getenv("SEUIL_P95_MS", "300"))
SEUIL_ECHECS = float(os.getenv("SEUIL_ECHECS", "0.01"))
