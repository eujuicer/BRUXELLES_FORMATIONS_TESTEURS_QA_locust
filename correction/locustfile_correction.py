from locust import HttpUser, task, between, constant
import random

# A changer dans le on start
keyword_list = ["jazz", "electro", "QA", "cloud"]

# PascalCase pour le nom des classes
class Visiteur(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)
    weight = 3

    def on_start(self):
        response = self.client.get("/api/events", name="/api/events [init]")
        events_list = response.json()

        self.events_id = [event["id"] for event in events_list]

        self.events_city= list({event["city"] for event in events_list})

        # Faire fail un user sur deux
        # dead = random.randint(1, 2)
        # if dead == 1:
        #     raise ValueError
        
        return super().on_start()
    
    @task(2)
    def seek_city(self):
        random_city = random.choice(self.events_city)
        with self.client.get(f"/api/events", params={"city": random_city}, name="/api/events?city=[random_city]", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            resultats = response.json()
            if not resultats: # if len(resultats) == 0 // if resultats == []
                response.failure(f"Aucun event à {random_city}")
            elif any(e["city"] != random_city for e in resultats):
                response.failure("Pas toutes les villes sont ok")

            # wrong = [e["city"] for e in city if e["city"] != random_city] === même chose que en haut
            # if wrong:
            #     response.failure(f"Seek city '{random_city}': event in another city ({wrong[0]})")


    @task(2)
    def seek_keyword(self):
        random_key_word = random.choice(keyword_list)
        with self.client.get(f"/api/events", params={"q": random_key_word}, name="/api/events?q=[random_key_word]", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            resultats = response.json()
            if not resultats: # if len(resultats) == 0 // if resultats == []
                response.failure(f"Aucun event à {random_key_word}")
            elif any(random_key_word.lower() not in e["title"].lower() for e in resultats):
                response.failure("Echoué, mot cles pas presents partout")



    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    @task(5)
    def consulter_detail(self):
        # Pouir faire fail des requetes volontairement
        # dead = random.randint(1, 2)
        # if dead == 1:
        #     raise ValueError
        event_id = random.choice(self.events_id)
        with self.client.get(f"/api/events/{event_id}", name="/api/events/[id]", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f'HTTP {response.status_code}')
                return
            event = response.json()
            if event["id"] != event_id:
                response.failure(f"Event {event["id"]} recu au lieu de l'event {event_id}")
            elif not event["categories"]:
                response.failure(f"Event {event_id} sans categorie de billets")



class Veilleur(HttpUser):
    host = "http://localhost:8000"
    wait_time = constant(5)

    @task
    def veiller(self):
        self.client.get("/api/health")


class ClientConnecte(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        auth_data = {
            "username": "client@eventflow.test",
            "password": "client1234"
        }

        response = self.client.post('/api/auth/token', data=auth_data)
        response.raise_for_status()
        
        credentials = response.json()

        token: str = credentials["access_token"]
        type: str = credentials["token_type"]

        self.client.headers["Authorization"] = f"{type.capitalize()} {token}"

        return super().on_start()

# Corr exo2
""" 1
10 utilisateurs => RPS attendu ? (10 * 1 / (0.1 + 2)) => 10 / 2.1
=== Plus ou moins RPS de 5
"""

"""2
1 Veilleur => (1 * 1) / (0.01 + 5) => 1 / 5 ===> 0.2 RPS
Pour 2 RPS => 10 veilleurs
"""

"""3
5 utilisateurs à 0 wait_time => ((5 * 1) / (0.01 + 0))
=> RPS attendu = 500 RPS
"""
