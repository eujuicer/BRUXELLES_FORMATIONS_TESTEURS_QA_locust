# logging : module de Python (pas de Locust) pour écrire des messages dans le terminal (exo 9).
import logging
# random : tirer au hasard un événement, un mot-clé ou une ville.
import random

# HttpUser        : classe de base d'un utilisateur virtuel qui parle HTTP.
# between         : attente aléatoire entre deux tâches.
# constant_pacing : une tâche toutes les N secondes exactement (exo 1).
# task            : transforme une méthode en tâche que Locust exécute.
# events          : permet de brancher une fonction sur la fin du test (exo 9).
from locust import HttpUser, between, constant_pacing, task, events

# config.py (dans ce dossier) lit le fichier .env : adresse de l'API, comptes, seuils.
# Rien de sensible n'est écrit dans le code : les mots de passe restent dans .env,
# qui n'est jamais envoyé sur GitHub. Modèle à copier : .env.example.
import config

# Exo 3 : mots-clés partagés par tous les visiteurs (définis une seule fois, en haut).
mots_cles = ["jazz", "electro", "QA", "cloud"]


# Connexion commune à ClientConnecte et Organisateur : écrite UNE fois ici
# au lieu d'être copiée dans les deux classes. "user" = l'utilisateur virtuel
# qui se connecte (on lui passe self).
def se_connecter(user, email, password):
    auth_data = {
        "username": email,
        "password": password
    }
    # POST : on ENVOIE des données. data= les envoie comme un formulaire.
    # Cette requête est lente (environ 250 ms) : le serveur vérifie le mot de passe.
    response = user.client.post('/api/auth/token', data=auth_data)
    # Statut d'erreur -> exception. Attention : une exception dans on_start
    # arrête l'utilisateur définitivement (visible seulement dans le terminal).
    response.raise_for_status()

    # Réponse : {"access_token": "eyJ...", "token_type": "bearer"}
    credentials = response.json()

    # ": str" = annotation de type (documentation, non vérifiée par Python).
    token: str = credentials["access_token"]
    type: str = credentials["token_type"]

    # headers (avec un s) : ajouté à TOUTES les requêtes suivantes de cet utilisateur.
    # Format exact "Bearer <token>" avec un espace, sinon le serveur répond 401.
    user.client.headers["Authorization"] = f"{type.capitalize()} {token}"


# Un internaute qui consulte le catalogue.
class Visiteur(HttpUser):
    # Adresse de l'API (EVENTFLOW_HOST dans .env) : les URL des requêtes sont
    # relatives à celle-ci. L'option -H de la ligne de commande la remplace.
    host = config.HOST
    # Attente aléatoire de 1 à 3 s (moyenne 2 s) -> environ 0,5 requête/s par visiteur (exo 2).
    wait_time = between(1, 3)
    # Exo 7 : poids de la CLASSE = part des utilisateurs qu'elle reçoit.
    # 1 organisateur pour 3 visiteurs -> Visiteur 3, Organisateur 1.
    # Utilisateurs d'une classe = total × poids ÷ somme des poids (3+1+1+1 = 6).
    # 20 utilisateurs -> Visiteur 10, Veilleur 3, Organisateur 3, ClientConnecte 4.
    weight = 3

    # on_start : exécuté UNE fois par visiteur, à son démarrage (son initialisation).
    def on_start(self):
        # name="[init]" : ligne à part dans les statistiques, pour ne pas fausser
        # celle du catalogue (cette requête est plus lente : tout le monde arrive en même temps).
        response = self.client.get("/api/events", name="/api/events [init]")
        # .json() : le texte JSON devient une liste de dictionnaires Python.
        events_list = response.json()

        # On garde les id du catalogue réel : aucun id écrit en dur.
        self.events_id = [event["id"] for event in events_list]
        # Exo 4 : { } = un set, qui supprime les doublons ; list() car random.choice
        # n'accepte pas un set. On réutilise la réponse : aucune requête en plus.
        self.villes = list({event["city"] for event in events_list})

        return super().on_start()

    # @task(n) : poids de la tâche. Total 3+5+2+2 = 12 -> catalogue 25 %,
    # détail 42 %, mot-clé 17 %, ville 17 % des requêtes.
    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.events_id)
        # name= regroupe tous les id sur une seule ligne "/api/events/[id]".
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")

    # Exo 3 (recherche) + exo 5 (vérification du contenu).
    @task(2)
    def recherche_mot_random(self):
        mot = random.choice(mots_cles)
        # catch_response=True : c'est NOUS qui jugeons la réponse. Sans ça, Locust
        # ne regarde que le statut (< 400 = succès) et ne lit jamais le contenu.
        # Le verdict est enregistré à la FIN du bloc with : tout vérifier dedans.
        with self.client.get(
            "/api/events",
            # params= : Locust construit l'URL /api/events?q=jazz.
            params={"q": mot},
            # Les 4 mots-clés sur une seule ligne des statistiques.
            name="/api/events?q=[mot]",
            catch_response=True,
        ) as response:
            # Le statut d'abord : sur une page d'erreur, response.json() planterait.
            if response.status_code != 200:
                # failure() : déclare l'échec, le message s'affiche dans l'onglet Failures.
                response.failure(f"Recherche mot-clé '{mot}' : HTTP {response.status_code}")
                return

            resultats = response.json()

            # Une liste vide vaut "faux" : not resultats = aucun résultat.
            if not resultats:
                response.failure(f"Recherche mot-clé '{mot}' : aucun résultat")
            # any() : vrai si AU MOINS UN titre ne contient pas le mot-clé.
            # .lower() partout : l'API ignore la casse ("QA" trouve "qa").
            elif any(mot.lower() not in e["title"].lower() for e in resultats):
                response.failure(f"Recherche mot-clé '{mot}' : un titre ne contient pas le mot-clé")

    # Exo 4 (recherche par ville) + exo 5 (vérification). Même principe qu'au-dessus.
    @task(2)
    def recherche_ville(self):
        # La ville vient du catalogue réel : marche sur n'importe quelle base.
        ville = random.choice(self.villes)
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

            if not resultats:
                response.failure(f"Recherche ville '{ville}' : aucun résultat")
            # Comparaison exacte (!=) : le filtre city respecte la casse
            # ("bruxelles" renvoie une liste vide).
            elif any(e["city"] != ville for e in resultats):
                response.failure(f"Recherche ville '{ville}' : un événement est dans une autre ville")


# Exo 1 : la sonde de supervision. Pas de weight -> poids 1 par défaut.
class Veilleur(HttpUser):
    host = config.HOST
    # Une requête toutes les 5 s EXACTEMENT, temps de réponse compris (0,2 requête/s).
    # constant(5) attendrait 5 s APRÈS la réponse : le rythme dériverait.
    wait_time = constant_pacing(5)

    # Une seule tâche : @task sans poids suffit.
    @task
    def check_vie(self):
        self.client.get("/api/health")


# Un client connecté à son compte.
class ClientConnecte(HttpUser):
    host = config.HOST
    wait_time = between(2, 5)
    weight = 1

    # Se connecter une seule fois au démarrage ; les tâches réutilisent le token.
    # Le compte vient de .env (CLIENT_EMAIL, CLIENT_PASSWORD).
    def on_start(self):
        se_connecter(self, config.CLIENT_EMAIL, config.CLIENT_PASSWORD)
        return super().on_start()

    # Ces URL exigent d'être connecté (sinon 401).
    @task(3)
    def consulter_mes_commandes(self):
        self.client.get("/api/orders/me")

    @task(4)
    def consulter_profil(self):
        self.client.get('/api/auth/me')

    # Exo 7 bonus : un client ne doit PAS accéder au back-office.
    @task(1)
    def tenter_acces_back_office(self):
        with self.client.get(
            '/api/admin/summary',
            # Ligne à part : ne pas mélanger les 403 du client et les 200 de l'organisateur.
            name="/api/admin/summary [client interdit]",
            catch_response=True,
        ) as response:
            # 403 (interdit) = la porte est fermée = c'est le BON résultat.
            # success() force le verdict "réussi" (par défaut, >= 400 serait un échec).
            if response.status_code == 403:
                response.success()
            # 200 = faille de sécurité, 401 = client plus reconnu, 500 = serveur planté.
            else:
                response.failure(f"Back-office accessible à un client : HTTP {response.status_code}")


# Exo 7 : un organisateur qui suit ses ventes dans le back-office.
class Organisateur(HttpUser):
    host = config.HOST
    # Trafic rare : entre 5 et 10 s entre deux actions.
    wait_time = between(5, 10)
    # 1 organisateur pour 3 visiteurs.
    weight = 1

    # Même connexion que ClientConnecte, avec le compte organisateur (ORGA_* dans .env).
    def on_start(self):
        se_connecter(self, config.ORGA_EMAIL, config.ORGA_PASSWORD)
        return super().on_start()

    # Réponse = un DICTIONNAIRE : {"events": 4, "published": 4, "total_sold": 0, ...}
    @task(1)
    def consulter_tableau_de_bord(self):
        with self.client.get('/api/admin/summary', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Tableau de bord : HTTP {response.status_code}")
                return

            # On lit un champ avec summary["nom_du_champ"].
            summary = response.json()

            # Règle métier : un événement publié est forcément un événement,
            # donc published ne peut jamais dépasser events.
            if summary["published"] > summary["events"]:
                response.failure(
                    f"Tableau de bord : {summary['published']} publiés "
                    f"pour {summary['events']} événements"
                )

    # Réponse = une LISTE : [{"id": 4, "capacity": 40, "sold": 0, ...}, ...]
    # Environ 3 fois plus lent que /api/events : le serveur calcule les ventes.
    @task(2)
    def consulter_ventes_par_evenements(self):
        with self.client.get('/api/admin/events', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Ventes par événement : HTTP {response.status_code}")
                return

            ventes = response.json()

            if not ventes:
                response.failure("Ventes par événement : liste vide")
            # Existe-t-il au moins un événement qui a vendu plus que sa capacité ?
            elif any(e["sold"] > e["capacity"] for e in ventes):
                response.failure("Ventes par événement : un événement a vendu plus que sa capacité")


# Exo 9 : le critère de réussite. Une CI ne lit que le code de sortie :
# 0 = réussi, 1 = échoué. Les seuils viennent de .env :
# SEUIL_P95_MS=300 (p95 max en ms) et SEUIL_ECHECS=0.01 (1 % d'échecs max).
# Appelle la fonction UNE fois, à la fin du test entier (hors des classes).
@events.test_stop.add_listener
# Le paramètre doit s'appeler exactement "environment" : Locust passe environment=...
# et Python fait le lien par le nom. **kwargs récupère les autres arguments.
def evalue_resultats(environment, **kwargs):
    # stats.total = la ligne Aggregated du tableau.
    total = environment.stats.total
    # p95 : 95 % des requêtes ont répondu en moins de p95 ms.
    p95 = total.get_response_time_percentile(0.95)
    # %s et %.2f sont remplacés par les valeurs qui suivent ; %% affiche le caractère %.
    logging.info(
        "Bilan : %s requêtes, p95 = %s ms, échecs = %.2f %%",
        total.num_requests, p95, total.fail_ratio * 100,
    )

    # EN PREMIER : sans aucune requête, p95 = 0 et échecs = 0 %, donc un test
    # qui n'a rien fait passerait les deux autres conditions.
    if total.num_requests == 0:
        logging.error("Critère non respecté : aucune requête exécutée")
        # process_exit_code remplace le code de sortie de Locust : on devient le seul juge.
        environment.process_exit_code = 1
    # fail_ratio va de 0 (aucun échec) à 1 (100 %). Détecte l'API injoignable
    # (port 8001), même quand les erreurs sont rapides (sous Linux, en CI).
    elif total.fail_ratio > config.SEUIL_ECHECS:
        logging.error("Critère non respecté : %.2f %% d'échecs (max 1 %%)", total.fail_ratio * 100)
        environment.process_exit_code = 1
    # L'API répond, mais trop lentement.
    elif p95 > config.SEUIL_P95_MS:
        logging.error("Critère non respecté : p95 = %s ms (max %s ms)", p95, config.SEUIL_P95_MS)
        environment.process_exit_code = 1
    # Les trois conditions sont respectées.
    else:
        logging.info("Critère de réussite respecté")
        environment.process_exit_code = 0
