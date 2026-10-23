
import random

from locust import HttpUser, between, constant, task

mots_cles = ["jazz", "electro", "QA", "cloud"]
             
class Visiteur(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.get("/api/events", name="/api/events [init]")
        events_list = response.json()
        
        self.events_id = [event["id"] for event in events_list]
        self.villes = list({event["city"]for event in events_list})
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
        self.client.get("/api/events", params={"q": mot}, name="/api/events?q=[mot]")
    @task(2)
    def recherche_ville(self):
        ville = random.choice(self.villes)
        self.client.get("/api/events", params={"city": ville}, name="/api/events?city=[ville]")        



class Veilleur(HttpUser):
    host = "http://localhost:8000"
    wait_time = constant(5)

    @task
    def check_vie(self):
        self.client.get("/api/health")

