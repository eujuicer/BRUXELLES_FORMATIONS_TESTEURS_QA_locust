import logging
import random

from locust import HttpUser, between, constant_pacing, task, events

import config

mots_cles = ["jazz", "electro", "QA", "cloud"]


def se_connecter(user, email, password):
    auth_data = {
        "username": email,
        "password": password
    }
    response = user.client.post('/api/auth/token', data=auth_data)
    response.raise_for_status()

    credentials = response.json()

    token: str = credentials["access_token"]
    type: str = credentials["token_type"]

    user.client.headers["Authorization"] = f"{type.capitalize()} {token}"


class Visiteur(HttpUser):
    host = config.HOST
    wait_time = between(1, 3)
    weight = 3

    def on_start(self):
        response = self.client.get("/api/events", name="/api/events [init]")
        events_list = response.json()

        self.events_id = [event["id"] for event in events_list]
        self.villes = list({event["city"] for event in events_list})

        return super().on_start()

    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.events_id)
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")

    @task(2)
    def recherche_mot_random(self):
        mot = random.choice(mots_cles)
        with self.client.get(
            "/api/events",
            params={"q": mot},
            name="/api/events?q=[mot]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Recherche mot-clé '{mot}' : HTTP {response.status_code}")
                return

            resultats = response.json()

            if not resultats:
                response.failure(f"Recherche mot-clé '{mot}' : aucun résultat")
            elif any(mot.lower() not in e["title"].lower() for e in resultats):
                response.failure(f"Recherche mot-clé '{mot}' : un titre ne contient pas le mot-clé")

    @task(2)
    def recherche_ville(self):
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
            elif any(e["city"] != ville for e in resultats):
                response.failure(f"Recherche ville '{ville}' : un événement est dans une autre ville")


class Veilleur(HttpUser):
    host = config.HOST
    wait_time = constant_pacing(5)

    @task
    def check_vie(self):
        self.client.get("/api/health")


class ClientConnecte(HttpUser):
    host = config.HOST
    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        se_connecter(self, config.CLIENT_EMAIL, config.CLIENT_PASSWORD)
        return super().on_start()

    @task(3)
    def consulter_mes_commandes(self):
        self.client.get("/api/orders/me")

    @task(4)
    def consulter_profil(self):
        self.client.get('/api/auth/me')

    @task(1)
    def tenter_acces_back_office(self):
        with self.client.get(
            '/api/admin/summary',
            name="/api/admin/summary [client interdit]",
            catch_response=True,
        ) as response:
            if response.status_code == 403:
                response.success()
            else:
                response.failure(f"Back-office accessible à un client : HTTP {response.status_code}")


class Organisateur(HttpUser):
    host = config.HOST
    wait_time = between(5, 10)
    weight = 1

    def on_start(self):
        se_connecter(self, config.ORGA_EMAIL, config.ORGA_PASSWORD)
        return super().on_start()

    @task(1)
    def consulter_tableau_de_bord(self):
        with self.client.get('/api/admin/summary', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Tableau de bord : HTTP {response.status_code}")
                return

            summary = response.json()

            if summary["published"] > summary["events"]:
                response.failure(
                    f"Tableau de bord : {summary['published']} publiés "
                    f"pour {summary['events']} événements"
                )

    @task(2)
    def consulter_ventes_par_evenements(self):
        with self.client.get('/api/admin/events', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Ventes par événement : HTTP {response.status_code}")
                return

            ventes = response.json()

            if not ventes:
                response.failure("Ventes par événement : liste vide")
            elif any(e["sold"] > e["capacity"] for e in ventes):
                response.failure("Ventes par événement : un événement a vendu plus que sa capacité")


@events.test_stop.add_listener
def evalue_resultats(environment, **kwargs):
    total = environment.stats.total
    p95 = total.get_response_time_percentile(0.95)
    logging.info(
        "Bilan : %s requêtes, p95 = %s ms, échecs = %.2f %%",
        total.num_requests, p95, total.fail_ratio * 100,
    )

    if total.num_requests == 0:
        logging.error("Critère non respecté : aucune requête exécutée")
        environment.process_exit_code = 1
    elif total.fail_ratio > config.SEUIL_ECHECS:
        logging.error("Critère non respecté : %.2f %% d'échecs (max 1 %%)", total.fail_ratio * 100)
        environment.process_exit_code = 1
    elif p95 > config.SEUIL_P95_MS:
        logging.error("Critère non respecté : p95 = %s ms (max %s ms)", p95, config.SEUIL_P95_MS)
        environment.process_exit_code = 1
    else:
        logging.info("Critère de réussite respecté")
        environment.process_exit_code = 0