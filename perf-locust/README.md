# Tests de performance EventFlow avec Locust

Exercices de la formation Testeur QA (Bruxelles Formation) : tests de charge de l'API EventFlow.

## Contenu

| Fichier | Rôle |
|---|---|
| `locustfile.py` | Le scénario de test (lancé par défaut par `locust`) |
| `locustfile_explique.py` | Le même code, commenté ligne par ligne |
| `config.py` | Lit la configuration depuis `.env` |
| `.env.example` | Modèle de configuration à copier en `.env` |
| `requirements.txt` | Dépendances Python |
| `resultats/` | Résultats CSV des tests headless |

## Installation

Prérequis : Python 3 et l'API EventFlow lancée sur http://localhost:8000.

Le dossier du dépôt contient un seul environnement virtuel (`.venv`, à la racine) ; la configuration (`.env`) est dans `perf-locust/`.

```bat
python -m venv .venv
.venv\Scriptsctivate.bat
pip install -r perf-locustequirements.txt
cd perf-locust
copy .env.example .env
```

Ensuite, complète `.env` avec les mots de passe des comptes de test (voir `LOCUST_EXERCICES.md`).

## Lancer

```bat
locust                                   :: interface web sur http://localhost:8089
locust Visiteur                          :: une seule classe
locust -f locustfile_explique.py         :: la version commentée
```

En headless, avec export CSV :

```bat
locust --headless -u 10 -r 5 -t 30s --reset-stats --only-summary --csv resultats/visiteur Visiteur
echo %errorlevel%                        :: 0 = critère respecté, 1 = échec
```

## Profils d'utilisateurs

| Classe | Poids | Comportement |
|---|---|---|
| `Visiteur` | 3 | Parcourt le catalogue, cherche par mot-clé et par ville |
| `Veilleur` | 1 | Sonde `/api/health` toutes les 5 s |
| `ClientConnecte` | 1 | Consulte ses commandes et son profil ; vérifie qu'il n'a pas accès au back-office |
| `Organisateur` | 1 | Consulte le tableau de bord et les ventes |

## Critère de réussite

À la fin du test, le code de sortie vaut `1` si :
- aucune requête n'a été exécutée ;
- plus de `SEUIL_ECHECS` des requêtes ont échoué (1 % par défaut) ;
- le p95 global dépasse `SEUIL_P95_MS` (300 ms par défaut).

Sinon, il vaut `0`. Les seuils se règlent dans `.env`.
