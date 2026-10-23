from locust import HttpUser, task, between, constant, constant_pacing

class Visiteur(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    @task
    def consulter_catalogue(self):
        self.client.get("/api/events")

class Veilleur(HttpUser):
    host = "http://localhost:8000"
    wait_time = constant(5)

    @task
    def check_vie(self):
        self.client.get("/api/health")
