from locust import HttpUser, task, between, constant
import random

keyword_list = ["jazz", "electro", "QA", "cloud"]

# PascalCase pour le nom des classes
class Visiteur(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.get("/api/events", name="/api/events [init]")
        events_list = response.json()

        self.events_id = [event["id"] for event in events_list]

        self.events_city= list({event["city"] for event in events_list})
        
        return super().on_start()
    
    @task(2)
    def seek_city(self):
        random_city = random.choice(self.events_city)
        self.client.get(f"/api/events", params={"city": random_city}, name="/api/events?city=[random_city]")

    @task(2)
    def seek_keyword(self):
        random_event = random.choice(keyword_list)
        self.client.get(f"/api/events", params={"q": random_event}, name="/api/events?q=[random_event]")


    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.events_id)
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")


class Veilleur(HttpUser):
    host = "http://localhost:8000"
    wait_time = constant(5)

    @task
    def veiller(self):
        self.client.get("/api/health")

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
