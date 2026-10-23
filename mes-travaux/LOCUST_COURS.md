# Tests de performance avec Locust

> **Tests d'API** : je sais vérifier qu'EventFlow répond correctement à **une** requête.
> **Aujourd'hui** : je sais vérifier qu'il reste rapide et correct quand **beaucoup** de monde l'utilise en même temps.

On ne réapprend ni Python ni les requêtes HTTP. On découvre un nouvel outil, Locust, et surtout une nouvelle question : que devient une application quand la charge augmente ?

Le fil de la séance :

1. Je comprends ce qu'on mesure dans un test de performance.
2. Je crée un premier utilisateur virtuel.
3. Je comprends d'où vient la charge réelle.
4. Je décris un comportement réaliste : plusieurs tâches, pondérées.
5. Je prépare mes utilisateurs avec des données réelles.
6. Je vérifie que les réponses sont justes, pas seulement rapides.
7. Je reconnais un test qui plante.
8. J'ajoute des utilisateurs authentifiés.
9. Je lance mes tests sans interface.
10. Je fais juger mes tests automatiquement.
11. Je termine par une mission de montée en charge.

Tout se construit dans **un seul fichier**, `locustfile.py`. À la fin de la séance, il décrira quatre types d'utilisateurs :

```text
locustfile.py
    critère de réussite      juge le test à la fin
    Visiteur                 parcourt le catalogue, ouvre des fiches, fait des recherches
    Veilleur                 sonde de supervision
    ClientConnecte           consulte ses commandes et son profil
    Organisateur             consulte le back-office
```

Ce fichier n'est pas donné d'avance. Il va **grandir**, au fur et à mesure que les besoins apparaissent.

Les exercices sont dans `LOCUST_EXERCICES.md`. Le cours indique où ils s'insèrent.

---

## 0. Avant de commencer

EventFlow doit tourner sur `http://localhost:8000`, en mode normal : http://localhost:8000/api/config doit afficher `"seed_bugs": false`. La documentation interactive de l'API reste votre référence : http://localhost:8000/docs.

Locust s'installe dans un environnement virtuel dédié, dans un dossier `perf-locust/`.

> **Règle :** on ne teste que **son propre** EventFlow, sur `localhost`. Jamais un site public, une API tierce ou le poste d'un collègue. On ne dépasse pas 200 utilisateurs virtuels.

➡️ **Exercice 0** — Mise en place.

---

## 1. Ce qu'on mesure

### 1.1 Rapide, et correct

Vos tests PyTest prouvent qu'une réservation fonctionne pour *un* utilisateur. Ils ne disent rien de ce qui se passe quand des milliers de personnes ouvrent la page du Festival Jazz à l'ouverture des ventes. Un test de performance observe une application **sous une charge donnée**, avec deux questions : reste-t-elle rapide ? Reste-t-elle correcte ?

| Type de test | Question | Exemple EventFlow |
|---|---|---|
| Charge (*load*) | Tient-on la charge prévue ? | 300 visiteurs un soir de semaine |
| Stress | Où et comment ça casse ? | Augmenter jusqu'à la dégradation |
| Pic (*spike*) | Absorbe-t-on un afflux brutal ? | Ouverture des ventes à 10 h |
| Endurance (*soak*) | Se dégrade-t-on avec le temps ? | Un week-end de ventes continues |

Ces tests utilisent tous le même outil et le même script. Seule la forme de la charge change.

### 1.2 Le vocabulaire

- **Utilisateurs concurrents** : actifs en même temps. Un visiteur qui lit la description d'un concert est actif, mais n'envoie aucune requête.
- **RPS** : requêtes par seconde. C'est le **débit** qui charge le serveur, pas le nombre d'utilisateurs.
- **Temps de réponse** : de l'envoi de la requête à la réponse complète, mesuré côté client.
- **Percentile** : le p95 est la valeur sous laquelle se trouvent 95 % des mesures. La médiane est le p50.

### 1.3 Pourquoi pas la moyenne ?

100 consultations : 90 répondent en 50 ms, 10 en 2 000 ms.

- moyenne : (90 × 50 + 10 × 2 000) / 100 = **245 ms** ;
- médiane : **50 ms** ;
- p95 : **2 000 ms**.

Personne n'a attendu 245 ms. Et un visiteur sur dix a attendu deux secondes. On lit toujours **la médiane** (l'expérience typique) **et un percentile élevé** (les cas lents).

### 1.4 Ce que Locust ne fait pas

Locust génère de la charge et mesure ce que voit le client. Il ne dit pas **pourquoi** une requête est lente : processeur, base de données, réseau... Pour le savoir, il faut observer le serveur.

---

## 2. Un premier utilisateur virtuel

### 2.1 On décrit un type d'utilisateur

Avec Locust, on ne décrit pas une requête : on décrit un **type d'utilisateur**, ce qu'il fait et à quel rythme. Au lancement, on choisit combien d'utilisateurs de ce type simuler.

Premier type : un visiteur qui consulte le catalogue.

```python
from locust import HttpUser, task, between


class Visiteur(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 3)

    @task
    def consulter_catalogue(self):
        self.client.get("/api/events")
```

| Élément | Rôle |
|---|---|
| `HttpUser` | Classe de base. Locust crée **une instance par utilisateur simulé**, chacune avec ses propres attributs. |
| `host` | URL de base de l'API, **sans `/` final** : Locust colle l'hôte et le chemin, et `.../` + `/api/events` donnerait `//api/events`. |
| `wait_time` | Le temps de « réflexion » après chaque tâche. `between(1, 3)` : aléatoire entre 1 et 3 s. `constant(n)` : toujours `n` secondes. |
| `@task` | Déclare une méthode comme une action que l'utilisateur répète. |
| `self.client` | Une session `requests`, que vous savez déjà utiliser. Différence : **chaque requête est chronométrée**. Un `requests.get` direct n'apparaîtrait nulle part. |

### 2.2 Lancer et lire

```bash
locust
```

Locust cherche `locustfile.py` dans le dossier courant. L'interface s'ouvre sur http://localhost:8089 : nombre d'utilisateurs, *ramp up* (combien en démarrer par seconde), puis *Start*.

- **Statistics** : une ligne par requête ; *Current RPS*, médiane, 95e percentile.
- **Charts** : débit, temps de réponse, nombre d'utilisateurs.
- **Failures** / **Exceptions** : ce qui a échoué (section 7).

Locust lit le fichier **au démarrage** : après chaque modification, `Ctrl+C` dans le terminal, puis on relance.

### 2.3 Utilisateur, tâche, requête

- Un **utilisateur virtuel** répète une boucle : choisir une tâche, l'exécuter, attendre.
- Une **tâche** est une action : « consulter le catalogue ».
- Une **requête** est un appel HTTP. Une tâche peut en faire plusieurs.

Les statistiques de Locust sont **par requête**.

### 2.4 Plusieurs classes

Un fichier peut contenir plusieurs classes d'utilisateurs. Par défaut, Locust **répartit** les utilisateurs demandés entre elles. Pour n'en lancer qu'une :

```bash
locust Visiteur
```

➡️ **Exercice 1** — Le veilleur.

---

## 3. D'où vient la charge

### 3.1 Utilisateurs ≠ débit

5 visiteurs ne produisent pas 5 requêtes par seconde. Chaque utilisateur boucle : une tâche (le temps de réponse), puis une attente. Il produit donc environ :

```
1 / (temps de réponse + attente moyenne)    requêtes par seconde
```

Et pour tout le test :

```
RPS ≈ utilisateurs × requêtes par tâche / (temps de réponse + attente moyenne)
```

Avec `between(1, 3)`, l'attente moyenne est de 2 s ; le catalogue répond en quelques millisecondes. Un visiteur fait donc environ 0,5 requête par seconde, et 5 visiteurs environ **2,5 RPS**.

« Notre test simule 200 utilisateurs » ne dit donc presque rien : selon le temps d'attente, ces 200 utilisateurs peuvent produire 7 RPS... ou plusieurs milliers.

### 3.2 Quand le serveur ralentit

Le temps de réponse est au dénominateur. Si le serveur se met à répondre en 2 s au lieu de 10 ms, chaque utilisateur boucle moins vite : **le débit baisse alors que le nombre d'utilisateurs ne change pas**.

Sur le graphique, un RPS qui plafonne pendant que les utilisateurs augmentent est un signe de **saturation**.

Et c'est une limite de l'outil : les utilisateurs virtuels ralentissent avec le serveur. Les vrais clients, eux, ne ralentissent pas quand le site rame : ils rafraîchissent la page.

### 3.3 Le *ramp up* n'est pas un débit

Le *ramp up* (ou *spawn rate*) est le nombre d'utilisateurs **démarrés** par seconde. 100 utilisateurs avec un *ramp up* de 10 mettent 10 s à arriver ; ensuite, c'est la formule qui décide du débit.

Pendant cette montée, la charge n'est pas encore celle qu'on veut mesurer. On verra comment l'écarter des statistiques à la section 9.

➡️ **Exercice 2** — Prévoir avant de mesurer.

---

## 4. Un comportement réaliste

### 4.1 Plusieurs tâches, pondérées

Un vrai visiteur ne recharge pas la liste en boucle. Il ouvre des fiches, `GET /api/events/{id}`, bien plus souvent :

```python
import random

# ...


class Visiteur(HttpUser):
    # ... host, wait_time

    @task(3)
    def consulter_catalogue(self):
        self.client.get("/api/events")

    @task(5)
    def consulter_detail(self):
        event_id = random.choice([1, 2, 3, 4])
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")
```

Le nombre passé à `@task(n)` est un **poids** : avec 3 et 5, le catalogue est choisi 3 fois sur 8. Les poids traduisent une hypothèse sur l'usage réel ; dans un vrai projet, ils viennent des statistiques de fréquentation.

L'onglet *Current Ratio* affiche la répartition prévue.

### 4.2 `name=` : une ligne par endpoint

Sans `name`, `/api/events/1`, `/api/events/2`, `/api/events/3`... apparaissent chacun sur **une ligne** dans les statistiques. Avec des milliers d'événements, le tableau devient illisible, et chaque ligne contient trop peu de mesures pour que ses percentiles veuillent dire quelque chose.

`name="/api/events/[id]"` regroupe toutes ces requêtes sous une seule étiquette. L'URL réellement appelée ne change pas.

La même chose vaut pour les paramètres : `params={"q": "jazz"}` et `params={"q": "QA"}` font deux lignes différentes. **Dès qu'une partie de l'URL varie, on donne un `name`.**

### 4.3 Toutes les requêtes n'ont pas le même coût

En lançant ce visiteur, on constate que le détail est environ **deux fois plus lent** que le catalogue. Ce n'est pas un hasard : le catalogue fait une requête SQL ; le détail expire d'abord les réservations dépassées, puis calcule la disponibilité de chaque catégorie de billets, avec une requête SQL par catégorie.

Locust montre l'écart. C'est en lisant le code de l'API (`backend/app/routers/events.py`) qu'on comprend pourquoi.

➡️ **Exercice 3** — Rechercher par mot-clé.

---

## 5. Préparer l'utilisateur avec `on_start`

### 5.1 Ne pas supposer les données

`random.choice([1, 2, 3, 4])` suppose que les événements 1 à 4 existent. Sur votre base, qui a servi pendant plusieurs modules, ce n'est pas garanti. Un identifiant disparu produirait des `404`, comptés comme des échecs de l'application alors que c'est le **test** qui est faux.

Comme dans vos tests PyTest : une règle stable s'écrit dans le test ; une donnée se **découvre** au moment du test.

### 5.2 `on_start`

`on_start` est exécutée **une fois par utilisateur**, à son démarrage, avant sa première tâche. Son pendant, `on_stop`, est exécutée quand l'utilisateur s'arrête.

```python
class Visiteur(HttpUser):
    # ... host, wait_time

    def on_start(self):
        response = self.client.get("/api/events", name="/api/events [init]")
        catalogue = response.json()
        self.event_ids = [event["id"] for event in catalogue]

    # ...

    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.event_ids)
        self.client.get(f"/api/events/{event_id}", name="/api/events/[id]")
```

- `on_start` n'a pas de `@task` : Locust la reconnaît à son nom.
- `self.event_ids` appartient à **cet** utilisateur.
- La requête de démarrage a son propre nom, `[init]`. Toutes ces requêtes arrivent en même temps, pendant la montée en charge : on ne les mélange pas aux consultations normales.

Avec 10 utilisateurs, la ligne `[init]` compte exactement 10 requêtes, et n'augmente plus ensuite.

> Ce qui se fait **une fois** (charger des données, se connecter) va dans `on_start`. Jamais dans une tâche : l'action serait répétée à chaque itération.

➡️ **Exercice 4** — Des villes qui existent vraiment.

---

## 6. Un statut 200 ne prouve rien

### 6.1 Un test vert qui ne mesure rien

Une recherche par ville, écrite un peu vite :

```python
self.client.get("/api/events", params={"city": "bruxelles"})
```

Lancée sous charge, cette ligne est irréprochable : aucun échec, l'endpoint le plus rapide du tableau. Dans le navigateur, http://localhost:8000/api/events?city=bruxelles renvoie... `[]`. Le filtre `city` d'EventFlow exige la casse exacte : `Bruxelles`.

Le test mesurait la vitesse à laquelle l'API renvoie une liste vide, et rien ne l'a signalé. Par défaut, Locust considère qu'une requête a réussi **dès que son statut est inférieur à 400**. Il ne lit pas le contenu.

D'autres défauts seraient tout aussi invisibles : un détail qui renvoie un **autre** événement que celui demandé, une réponse incomplète...

### 6.2 `catch_response` : c'est le test qui juge

```python
    @task(5)
    def consulter_detail(self):
        event_id = random.choice(self.event_ids)
        with self.client.get(
            f"/api/events/{event_id}",
            name="/api/events/[id]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            event = response.json()
            if event["id"] != event_id:
                response.failure(f"Événement {event['id']} reçu au lieu de {event_id}")
            elif not event["categories"]:
                response.failure(f"Événement {event_id} sans catégorie de billets")
```

| Élément | Rôle |
|---|---|
| `catch_response=True` + `with` | Locust attend la **sortie du bloc** pour enregistrer le verdict. |
| `response.failure("message")` | Déclare la requête échouée. Le message apparaît dans l'onglet *Failures*. |
| `response.success()` | Déclare la requête réussie, quel que soit son statut. |
| Ni l'un ni l'autre | La règle par défaut s'applique (statut < 400). |

Trois réflexes :

- **Le statut d'abord.** Si le serveur renvoie une page d'erreur, `response.json()` planterait. D'où le `return`.
- **Tout dans le `with`.** Une vérification écrite après le bloc n'a aucun effet : le verdict est déjà enregistré.
- **Rester léger.** Ce code s'exécute à **chaque** requête, dans le processus qui génère la charge. On vérifie un champ, pas un JSON Schema complet.

Les messages de `failure` sont regroupés par texte dans *Failures* : écrivez-les pour qu'un collègue comprenne sans lire le code.

### 6.3 Ce qu'une réponse ne peut pas montrer

La disponibilité renvoyée par le détail est calculée avec un plancher à zéro (`max(0, quota - vendus)`). Même si des billets étaient vendus au-delà du quota, l'API afficherait `available: 0`. Certains défauts ne se voient pas dans la réponse : il faut une autre source (le back-office, la base de données).

➡️ **Exercice 5** — Des recherches qui ne mentent pas.

---

## 7. Quand le test lui-même plante

Vous savez déclarer qu'une **réponse** est fausse. Mais quand c'est le **code du test** qui plante, Locust réagit autrement, et un test peut paraître vert sans rien mesurer.

| Famille d'échec | Exemple | Où la voir |
|---|---|---|
| Erreur HTTP | `401`, `500`, connexion refusée | *# Fails*, onglet *Failures* |
| Échec métier | `200` mais réponse fausse | *# Fails*, *Failures*, **seulement si on l'a vérifié** |
| Erreur de scénario | `KeyError` dans le code du test | terminal ; onglet *Exceptions* si l'erreur survient dans une tâche |

Deux comportements à connaître :

- une exception levée **dans un bloc `catch_response`** fait disparaître la requête des statistiques, et interrompt la tâche ;
- une exception levée **dans `on_start`** arrête l'utilisateur définitivement. Il n'est pas remplacé, et l'erreur n'apparaît que dans le terminal.

> 0 % d'échecs ne prouve rien tant qu'on n'a pas regardé *Exceptions*, le terminal, et le nombre d'utilisateurs réellement actifs.

➡️ **Exercice 6** — Casser pour comprendre.

---

## 8. Des utilisateurs authentifiés

### 8.1 Un autre type d'utilisateur

Une partie du trafic vient de clients connectés qui consultent leurs commandes et leur profil. Ils ne font pas la même chose que les visiteurs, ni au même rythme : c'est **une autre classe**.

Authentification EventFlow (vue en tests d'API) :

1. `POST /api/auth/token` avec `username` et `password` **en formulaire** (`data=...`, pas `json=...`, sinon `422`) ;
2. récupérer `access_token` ;
3. envoyer `Authorization: Bearer <token>` dans les requêtes suivantes.

Se connecter, c'est quelque chose qu'on fait **une fois** : `on_start`.

```python
class ClientConnecte(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        response = self.client.post(
            "/api/auth/token",
            data={"username": "client@eventflow.test", "password": "client1234"},
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {token}"

    @task(3)
    def consulter_mes_commandes(self):
        self.client.get("/api/orders/me")

    @task(1)
    def consulter_profil(self):
        self.client.get("/api/auth/me")
```

Et dans `Visiteur` : `weight = 3`.

| Élément | Rôle |
|---|---|
| `self.client.headers` | En-têtes de la session de **cet** utilisateur : le jeton s'applique à toutes ses requêtes suivantes. |
| `raise_for_status()` | Sans connexion, ce client ne produirait que des `401`. On préfère qu'il s'arrête (section 7). |
| `weight` | Proportion d'utilisateurs de chaque classe. Ici, 3 visiteurs pour 1 client. |

Un seul compte partagé par tous les clients virtuels, c'est acceptable **en lecture**.

### 8.2 Le coût de la connexion

`POST /api/auth/token` répond en quelques centaines de millisecondes, quand les autres endpoints répondent en quelques dizaines. Le mot de passe est vérifié avec bcrypt, un algorithme **volontairement lent**, pour résister aux attaques par force brute.

Conséquence directe du *ramp up* : si beaucoup de clients démarrent en même temps, leurs connexions se gênent. Un test de pic avec des centaines de clients connectés mesurerait d'abord... la tenue de l'authentification.

### 8.3 Pourquoi seulement des lectures ?

Réserver et payer écrivent en base. Chaque réservation bloque du stock pendant 10 minutes (l'Atelier QA n'a que 35 places), chaque paiement est définitif. Un test de charge qui écrit consomme ses propres données : au bout de quelques secondes, il ne mesure plus que des refus de stock. Il ne se lance que sur une base **jetable**, avec des données préparées pour toute la durée du test.

➡️ **Exercice 7** — L'organisateur.

---

## 9. Lancer sans interface

L'interface sert à explorer. Pour des mesures **reproductibles**, qu'on peut archiver et lancer dans un pipeline, on passe en ligne de commande :

```bash
locust --headless -u 20 -r 5 -t 30s --reset-stats --only-summary Visiteur
```

| Option | Rôle |
|---|---|
| `--headless` | Pas d'interface, démarrage immédiat |
| `-u` / `-r` | Utilisateurs / *ramp up* |
| `-t` | Durée (`30s`, `5m`…) |
| `--reset-stats` | Remet les statistiques à zéro une fois tous les utilisateurs démarrés |
| `--only-summary` | N'affiche que le bilan final |
| `--csv dossier/prefixe` | Enregistre les résultats en CSV |
| `Visiteur` (à la fin) | Ne lance que cette classe |

Le bilan contient deux tableaux : les statistiques (requêtes, échecs, moyenne, médiane, RPS), puis les percentiles de chaque ligne.

`--reset-stats` est indispensable pour mesurer un palier : pendant la montée en charge, il y a peu d'utilisateurs, les temps sont flatteurs.

➡️ **Exercice 8** — Comparer les profils (facultatif).

---

## 10. Faire juger le test automatiquement

### 10.1 Le besoin

Une CI ne lit pas de tableau. Elle regarde le **code de sortie** : `0` = réussi, `1` = échec. Par défaut, Locust renvoie `1` dès qu'une requête a échoué. On veut un critère qui a du sens pour l'équipe : **le p95 global ne dépasse pas 300 ms**.

Ce critère concerne **le test entier**, pas un utilisateur. `on_stop` ne convient pas : avec 100 utilisateurs, il serait calculé 100 fois, sur des statistiques incomplètes.

### 10.2 Les events

`locust.events` expose des points d'accroche sur la vie du test. On y attache une fonction **hors des classes** :

```python
import logging
import random

from locust import HttpUser, task, between, constant, events

SEUIL_P95_MS = 300


@events.test_stop.add_listener
def evaluer_resultats(environment, **kwargs):
    p95 = environment.stats.total.get_response_time_percentile(0.95)
    logging.info("Bilan : p95 = %s ms", p95)
    if p95 > SEUIL_P95_MS:
        logging.error("Critère de réussite non respecté.")
        environment.process_exit_code = 1
    else:
        environment.process_exit_code = 0
```

| Élément | Rôle |
|---|---|
| `@events.test_stop.add_listener` | Exécute la fonction **une fois**, à la fin du test. |
| `environment` | Accès au test : `stats.total` (ligne *Aggregated*), `process_exit_code`. |
| `**kwargs` | Toujours en fin de signature : Locust peut transmettre d'autres arguments. |
| `logging` | Écrit dans le journal de Locust, horodaté. C'est ce qu'on retrouve dans les logs d'un pipeline. |
| `process_exit_code` | Remplace le code de sortie de Locust : la fonction devient le seul juge. |

```bash
locust --headless -u 20 -r 5 -t 30s --only-summary Visiteur
echo $?                  # Windows : echo $LASTEXITCODE
```

Le critère porte sur le p95 **global**. Lancez toutes les classes à la fois : le p95 global reste de quelques dizaines de millisecondes, alors que chaque connexion en prend plusieurs centaines. Les connexions sont trop rares pour peser dans un percentile calculé sur toutes les requêtes. Un indicateur global peut donc **masquer** un endpoint lent : on choisit son critère, et la population testée, en conséquence.

➡️ **Exercice 9** — Un critère qui ne ment pas.

---

## 11. Mission

➡️ **Exercice 10** — Mission : montée en charge.

---

## Aide-mémoire

### Anatomie d'un `locustfile.py`

```text
imports
constantes (seuils, données de test)
@events...           ce qui concerne le test entier
class X(HttpUser)    un type d'utilisateur
    host, wait_time, weight
    on_start         ce qui se fait une fois
    @task(n)         ce qui se répète
```

### Commandes

```bash
locust                                   # interface : http://localhost:8089
locust Visiteur                          # une seule classe
locust --headless -u 50 -r 10 -t 60s --reset-stats --only-summary Visiteur
```

### Erreurs fréquentes

- `host` avec un `/` final.
- `requests.get` au lieu de `self.client.get` : aucune statistique.
- Oublier de relancer Locust après une modification.
- Raisonner en nombre d'utilisateurs au lieu de débit.
- Oublier `name=` sur une URL qui varie.
- Se connecter dans une tâche au lieu de `on_start`.
- Se contenter du statut HTTP.
- Écrire une vérification hors du bloc `with`.
- Lire la moyenne au lieu de la médiane et du p95.
- Conclure à 0 % d'échecs sans regarder *Exceptions* ni le terminal.
- Présenter un résultat obtenu sur un portable comme une capacité de production.

### Endpoints EventFlow utilisés

| Méthode | Route | Accès |
|---|---|---|
| GET | `/api/health` | public |
| GET | `/api/events` (`q`, `city`) | public |
| GET | `/api/events/{id}` | public |
| POST | `/api/auth/token` (formulaire) | public |
| GET | `/api/auth/me`, `/api/orders/me` | connecté |
| GET | `/api/admin/summary`, `/api/admin/events` | organisateur |
