# =============================================================================
# Tests de performance EventFlow avec Locust
#
# Lancer (depuis perf-locust/, environnement activé) :
#   locust -f locustfile_explique.py           -> toutes les classes, interface web sur http://localhost:8089
#   locust -f locustfile_explique.py Visiteur  -> seulement la classe Visiteur
# =============================================================================

# `random` sert à tirer au hasard un événement, un mot-clé ou une ville :
# chaque utilisateur virtuel fait ainsi des requêtes variées, comme un vrai visiteur.
import random

# Ce qu'on importe depuis Locust :
# - HttpUser        : la classe de base d'un "utilisateur virtuel" qui parle HTTP.
#                     Chaque classe qui en hérite = un type de comportement (un profil).
# - between         : attente ALÉATOIRE entre deux tâches (ex. entre 1 et 3 s).
# - constant_pacing : rythme FIXE : une tâche toutes les N secondes, quel que soit
#                     le temps de réponse (exo 1).
# - task            : décorateur qui transforme une méthode en "tâche" que Locust exécute.
from locust import HttpUser, between, constant_pacing, task


# --- Exo 3 : liste des mots-clés ---------------------------------------------
# Définie en haut du fichier (constante du module) : elle est partagée par
# tous les visiteurs, inutile de la recréer pour chacun.
mots_cles = ["jazz", "electro", "QA", "cloud"]


# =============================================================================
# Classe Visiteur : un internaute qui consulte le catalogue d'événements
# =============================================================================
class Visiteur(HttpUser):
    # Adresse de l'API testée. Toutes les URL de self.client.get(...) sont
    # relatives à cette adresse ("/api/events" -> http://localhost:8000/api/events).
    host = "http://localhost:8000"

    # Temps de réflexion entre deux tâches : un nombre aléatoire entre 1 et 3 s.
    # Moyenne = (1 + 3) / 2 = 2 s -> un visiteur fait environ 0,5 requête/s (exo 2).
    wait_time = between(1, 3)

    # -------------------------------------------------------------------------
    # on_start : exécuté UNE SEULE FOIS par visiteur, à son démarrage,
    # avant toute tâche. Idéal pour préparer des données (ici : la liste des
    # identifiants et des villes), comme un vrai visiteur qui arrive sur
    # la page d'accueil.
    # -------------------------------------------------------------------------
    def on_start(self):
        # name="... [init]" : cette requête apparaît sur sa propre ligne dans
        # les statistiques. Sinon elle serait mélangée avec les consultations
        # du catalogue faites par la tâche consulter_catalogue et fausserait
        # leurs chiffres.
        response = self.client.get("/api/events", name="/api/events [init]")

        # .json() transforme le texte JSON de la réponse en objets Python :
        # ici une liste de dictionnaires, un par événement.
        events_list = response.json()

        # Compréhension de liste : on garde uniquement le champ "id" de chaque
        # événement. On évite ainsi d'écrire des identifiants en dur dans le code.
        self.events_id = [event["id"] for event in events_list]

        # --- Exo 4 : les villes présentes dans le catalogue ------------------
        # { ... } avec une seule valeur = un SET : il élimine les doublons
        # (Bruxelles apparaît deux fois dans le catalogue, une seule fois ici).
        # list(...) : random.choice n'accepte pas un set, donc on le convertit.
        # On réutilise la réponse déjà reçue : AUCUNE requête supplémentaire.
        self.villes = list({event["city"] for event in events_list})

        # On appelle aussi le on_start de la classe parente (HttpUser).
        # Ici il ne fait rien, mais c'est une bonne habitude en orienté objet.
        return super().on_start()

    # -------------------------------------------------------------------------
    # Les tâches. Le nombre entre parenthèses est le POIDS : plus il est grand,
    # plus la tâche est choisie souvent.
    # Total des poids : 3 + 5 + 2 + 2 = 12, donc :
    #   catalogue 3/12 = 25 %, détail 5/12 ≈ 42 %,
    #   recherche mot-clé 2/12 ≈ 17 %, recherche ville 2/12 ≈ 17 %.
    # Après chaque tâche, Locust attend wait_time puis en tire une autre au hasard.
    # -------------------------------------------------------------------------

    # Consulter la liste complète des événements.
    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    # Consulter la fiche d'un événement tiré au hasard.
    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.events_id)
        # Sans name=, chaque id créerait sa propre ligne dans les statistiques
        # (/api/events/1, /api/events/2...). name= les regroupe sur une seule
        # ligne "/api/events/[id]", plus lisible et plus fiable statistiquement.
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")

    # --- Exo 3 : rechercher par mot-clé --------------------------------------
    # --- Exo 5 : + vérification du contenu de la réponse ---------------------
    @task(2)
    def recherche_mot_random(self):
        mot = random.choice(mots_cles)
        # params={"q": mot} : Locust (via la bibliothèque requests) construit
        # lui-même l'URL /api/events?q=jazz, en encodant correctement le texte.
        # name= : les 4 mots-clés sont regroupés sur UNE seule ligne.
        #
        # Exo 5 : catch_response=True + with -> c'est NOUS qui décidons si la
        # requête a réussi. Sans ça, Locust ne regarde que le statut HTTP
        # (< 400 = succès) et ne lit jamais le contenu.
        # Locust enregistre le verdict à la SORTIE du bloc with : toutes les
        # vérifications doivent donc être écrites à l'intérieur.
        with self.client.get(
            "/api/events",
            params={"q": mot},
            name="/api/events?q=[mot]",
            catch_response=True,
        ) as response:
            # 1) Le statut d'abord : sur une page d'erreur, response.json()
            #    planterait. On déclare l'échec et on sort (return).
            if response.status_code != 200:
                response.failure(f"Recherche mot-clé '{mot}' : HTTP {response.status_code}")
                return

            resultats = response.json()

            # 2) Au moins un résultat. Une liste vide vaut "faux" en Python,
            #    donc `not resultats` est vrai quand la liste est vide
            #    (équivaut à `len(resultats) == 0` ou `resultats == []`).
            if not resultats:
                response.failure(f"Recherche mot-clé '{mot}' : aucun résultat")
            # 3) Chaque titre contient le mot-clé.
            #    any(...) renvoie True dès qu'AU MOINS UN élément remplit la
            #    condition : "s'il existe un titre SANS le mot-clé -> échec".
            #    elif : on ne vérifie les titres que si la liste n'est pas vide.
            #    L'API ignore la casse ("QA" trouve "qa"), donc on compare tout
            #    en minuscules (.lower()).
            elif any(mot.lower() not in e["title"].lower() for e in resultats):
                response.failure(f"Recherche mot-clé '{mot}' : un titre ne contient pas le mot-clé")
            # Si aucun failure() n'est appelé, la règle par défaut s'applique :
            # statut 200 -> succès. Pas besoin d'appeler response.success().

    # --- Exo 4 : rechercher par ville ----------------------------------------
    # --- Exo 5 : + vérification du contenu de la réponse ---------------------
    @task(2)
    def recherche_ville(self):
        # La ville vient du catalogue réel (on_start) : le test fonctionne sur
        # n'importe quelle base EventFlow, sans nom de ville écrit dans le code.
        ville = random.choice(self.villes)
        # Même principe que la recherche par mot-clé (voir les commentaires au-dessus).
        with self.client.get(
            "/api/events",
            params={"city": ville},
            name="/api/events?city=[ville]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Recherche ville '{ville}' : HTTP {response.status_code}")
                return

            resultats = response.json()

            # Au moins un résultat : la ville vient du catalogue, donc elle a
            # forcément au moins un événement. Une liste vide = réponse fausse.
            if not resultats:
                response.failure(f"Recherche ville '{ville}' : aucun résultat")
            # Chaque événement est bien dans la ville demandée : "s'il existe
            # un événement dans une AUTRE ville -> échec". Comparaison exacte
            # (!=) : le filtre city d'EventFlow respecte la casse.
            elif any(e["city"] != ville for e in resultats):
                response.failure(f"Recherche ville '{ville}' : un événement est dans une autre ville")


# =============================================================================
# Exo 1 : classe Veilleur, la sonde de supervision de l'équipe d'exploitation
# =============================================================================
class Veilleur(HttpUser):
    host = "http://localhost:8000"

    # Une requête toutes les 5 secondes EXACTEMENT.
    # - constant_pacing(5) : Locust vise un cycle de 5 s. Si la requête prend
    #   0,1 s, il attend 4,9 s. Le rythme reste fixe, comme une vraie sonde.
    # - constant(5) aurait attendu 5 s APRÈS chaque réponse : le cycle ferait
    #   5 s + temps de réponse, donc il dériverait.
    # Débit d'un veilleur : 1 / 5 = 0,2 requête/s (exo 2).
    wait_time = constant_pacing(5)

    # Une seule tâche, donc pas besoin de poids : @task suffit.
    @task
    def check_vie(self):
        # La sonde vérifie simplement que l'API est en vie.
        self.client.get("/api/health")

# Remarque : aucune des deux classes ne définit de `weight`. Les deux ont donc
# le même poids, et Locust répartit les utilisateurs moitié-moitié
# (6 utilisateurs -> 3 Visiteurs + 3 Veilleurs).
