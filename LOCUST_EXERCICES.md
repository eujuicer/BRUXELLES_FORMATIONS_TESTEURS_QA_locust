# Tests de performance avec Locust — exercices

Tous les exercices enrichissent le **même** fichier `perf-locust/locustfile.py`. Gardez-le en ordre : les exercices suivants s'appuient sur ce que vous avez écrit avant.

Après chaque modification : `Ctrl+C` dans le terminal, puis relancez Locust.

---

## Exercice 0 — Mise en place

1. Vérifiez qu'EventFlow tourne :
   - http://localhost:8000/api/health répond `ok` ;
   - http://localhost:8000/api/config affiche `"seed_bugs": false`.
2. Créez le dossier `perf-locust/`, un environnement virtuel, et installez Locust :

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
   pip install locust==2.46.7
   locust --version
   ```

3. Créez un fichier vide `locustfile.py` dans `perf-locust/`.

**C'est prêt quand** `locust --version` affiche `2.46.7` depuis l'environnement activé.

---

## Exercice 1 — Le veilleur

L'équipe d'exploitation a mis en place une sonde de supervision : toutes les **5 secondes exactement**, elle vérifie que l'API est en vie avec `GET /api/health`. Cette sonde fait partie du trafic réel ; elle doit faire partie de votre test.

**Consignes**

1. Dans le même fichier, ajoutez une classe `Veilleur` qui reproduit cette sonde.
2. Lancez Locust avec **6** utilisateurs.

**Observez**

- Combien d'utilisateurs de chaque classe Locust a-t-il démarrés ? (journal du terminal, ou onglet *Current Ratio*)
- Combien de lignes dans *Statistics*, et lesquelles ?
- Relancez avec `locust Visiteur`. Qu'est-ce qui change ?

<details>
<summary>Indice</summary>

Relisez le tableau de la section 2.1 du cours : une des fonctions de `wait_time` donne une attente fixe. Pensez à l'importer.
</details>

**Mes réponses** — `wait_time = constant_pacing(5)` : une requête toutes les 5 s **exactement**. `constant(5)` attendrait 5 s *après* la réponse, donc le rythme dériverait.

- **Répartition** avec 6 utilisateurs : `{"Veilleur": 3, "Visiteur": 3}`. Sans `weight`, les deux classes ont le même poids.
- **Lignes dans *Statistics*** : une par endpoint (`/api/events`, `[init]`, `/api/events/[id]`, `/api/health`), plus *Aggregated*.
- **`locust Visiteur`** : seule cette classe est lancée, et la ligne `/api/health` disparaît.

---

## Exercice 2 — Prévoir avant de mesurer

Un testeur de performance prévoit **avant** de lancer. Sinon, il ne peut pas savoir si ce qu'il voit est normal.

**Consignes**

1. Calculez le RPS attendu avec **10 visiteurs**. Notez votre prévision, puis mesurez (classe `Visiteur` seule, 30 secondes).
2. Calculez le débit produit par **un** veilleur. Combien de veilleurs faudrait-il pour produire 2 RPS ?
3. Que se passerait-il si les visiteurs n'attendaient plus du tout entre deux tâches ? Notez une prévision, puis vérifiez-la : modifiez **temporairement** le temps d'attente de `Visiteur`, 5 utilisateurs, une quinzaine de secondes.
4. Expliquez le résultat de la question 3 avec la formule du cours. Relevez aussi la médiane : a-t-elle changé ?
5. **Remettez `between(1, 3)`.**

| Question | Prévision | Mesure |
|---|---|---|
| 10 visiteurs | ~5 RPS | 4,9 RPS |
| 1 veilleur | 0,2 RPS (10 veilleurs pour 2 RPS) | — |
| 5 visiteurs sans attente | RPS en forte hausse | 299,4 RPS (médiane 16 ms) |

**Mes calculs** — formule : RPS ≈ utilisateurs ÷ (temps de réponse + attente moyenne)

- **10 visiteurs** : attente moyenne de `between(1, 3)` = (1 + 3) ÷ 2 = 2 s. Un visiteur : 1 ÷ 2 = 0,5 RPS. Dix visiteurs : 10 × 0,5 = **5 RPS**. Mesuré : 4,9.
- **1 veilleur** : `constant_pacing(5)`, une requête toutes les 5 s, donc 1 ÷ 5 = **0,2 RPS**. Pour 2 RPS : 2 ÷ 0,2 = **10 veilleurs**. Contrôle : 3 veilleurs mesurés à 0,6 RPS = 3 × 0,2.
- **5 visiteurs sans attente** : temps de réponse moyen 16,71 ms = 0,01671 s. Un visiteur : 1 ÷ 0,01671 ≈ 60 RPS. Cinq visiteurs : 5 × 60 ≈ **300 RPS**. Mesuré : 299,4.
- **Médiane** : 16 ms sans attente. Le RPS a été multiplié par environ 120, mais le temps de réponse de l'API reste de quelques ms.

---

## Exercice 3 — Rechercher par mot-clé

Les visiteurs ne font pas que parcourir : ils cherchent. `GET /api/events` accepte un paramètre `q`, qui cherche dans le titre des événements (sans tenir compte de la casse).

**Consignes**

1. En haut du fichier, définissez une liste de mots-clés : `"jazz"`, `"electro"`, `"QA"`, `"cloud"`.
2. Ajoutez au `Visiteur` une tâche de **poids 2** qui recherche un mot-clé tiré au hasard dans cette liste.
3. Toutes les recherches doivent apparaître sur **une seule ligne** dans les statistiques.

**Observez** (10 visiteurs, une minute)

- Combien de lignes dans *Statistics* ? Une seule pour la recherche ?
- La répartition entre catalogue, détail et recherche correspond-elle à vos poids ? Calculez la proportion attendue pour chaque tâche.
- Où se place la recherche en temps de réponse, par rapport au catalogue et au détail ?

**Mes réponses** (10 visiteurs, 1 minute)

- **Une seule ligne**, grâce à `name="/api/events?q=[mot]"`.
- **Proportions attendues** : 3 + 5 + 2 = 10, donc catalogue 30 %, détail 50 %, recherche 20 % (25 % / 41,7 % / 16,7 % / 16,7 % une fois l'exo 4 ajouté). Mesuré sur 295 requêtes : 24,7 % / 40 % / 20,3 % / 14,9 %. C'est conforme, aux variations aléatoires près.
- **Temps de réponse (médiane)** : recherche 5 ms, catalogue 5 ms, détail 8 ms. La recherche ne coûte pas plus cher que le catalogue.

---

## Exercice 4 — Des villes qui existent vraiment

`GET /api/events` accepte aussi un paramètre `city`. On veut une recherche par ville qui fonctionne sur **n'importe quelle** base EventFlow, sans écrire de nom de ville dans le code.

**Consignes**

1. Au démarrage de chaque visiteur, en plus des identifiants, mémorisez la liste des villes présentes dans le catalogue, **sans doublon**.
2. Ajoutez une tâche de **poids 2** qui recherche les événements d'une ville tirée au hasard dans cette liste.
3. Une seule ligne dans les statistiques pour cette recherche.
4. N'ajoutez **aucune** requête de démarrage : vous avez déjà le catalogue.

**Observez**

- Combien de requêtes `[init]` avec 10 visiteurs ? Est-ce le même nombre qu'avant l'exercice ?
- Ouvrez dans le navigateur la recherche pour chacune de vos villes. Que renvoient-elles ?

<details>
<summary>Indice</summary>

Un `set` Python élimine les doublons. `random.choice` n'accepte pas un `set` : transformez-le en liste.
</details>

**Mes réponses** — `self.villes = list({event["city"] for event in events_list})`, dans `on_start`, en réutilisant la réponse du catalogue.

- **Requêtes `[init]`** : 10 pour 10 visiteurs, le même nombre qu'avant. Aucune requête ajoutée.
- **Résultats par ville** : `Bruxelles` → « Atelier QA & Test automatise » et « Nuit electro - Halles Saint-Gery » ; `Gand` → « Conference DevOps & Cloud 2026 » ; `Liege` → « Festival Jazz au Parc ». Attention : `?city=bruxelles` (minuscules) renvoie `[]`, car le filtre respecte la casse.

---

## Exercice 5 — Des recherches qui ne mentent pas

Vos deux recherches sont, pour l'instant, jugées uniquement sur leur statut HTTP. Elles pourraient renvoyer n'importe quoi.

**Consignes**

Ajoutez des vérifications aux deux recherches, pour qu'une réponse fausse soit déclarée en échec :

- **par mot-clé** : il y a au moins un résultat, et chaque titre renvoyé contient le mot-clé recherché ;
- **par ville** : il y a au moins un résultat, et chaque événement renvoyé est bien dans la ville demandée.

Vos messages d'échec doivent dire **quelle** recherche a échoué.

**Prouvez que vos vérifications fonctionnent.** Une vérification qu'on n'a jamais vue échouer ne prouve rien. Pour chacune des deux recherches :

1. sabotez **temporairement** la requête ou la vérification pour provoquer un échec ;
2. observez l'onglet *Failures* : le message est-il compréhensible sans lire le code ?
3. rétablissez.

**C'est terminé quand** 10 visiteurs pendant une minute ne produisent aucun échec, et que vous avez vu chacune de vos vérifications échouer au moins une fois.

**Mes réponses** — `catch_response=True` + `with` ; le statut d'abord, puis `if not resultats` (liste vide), puis `elif any(...)`.

| Sabotage temporaire | Échecs | Message dans *Failures* |
|---|---|---|
| `q = mot + "zzz"` | 100 % | `Recherche mot-clé 'jazz' : aucun résultat` |
| chercher `"xyz"` dans les titres | 100 % | `Recherche mot-clé 'electro' : un titre ne contient pas le mot-clé` |
| `city = ville.lower()` | 100 % | `Recherche ville 'Bruxelles' : aucun résultat` |
| comparer à `ville + "x"` | 100 % | `Recherche ville 'Gand' : un événement est dans une autre ville` |

Rétabli : 10 visiteurs pendant 1 minute, 306 requêtes, **0 échec**.

---

## Exercice 6 — Casser pour comprendre

Le but est de voir comment Locust réagit quand **le test** plante, pour savoir le reconnaître plus tard.

**Manipulation A.** Dans une de vos vérifications, remplacez un nom de champ de la réponse par un nom qui n'existe pas. Lancez 10 visiteurs pendant 30 secondes.

**Manipulation B.** Rétablissez le champ. Relancez en remplaçant `8000` par `8001` dans le champ *Host* de l'interface (rien n'écoute sur ce port).

Pour chaque manipulation, complétez :

| | Manipulation A | Manipulation B |
|---|---|---|
| L'endpoint concerné est-il dans *Statistics* ? | | |
| Colonne *# Fails* | | |
| Onglet *Exceptions* | | |
| Terminal | | |
| Compteur d'utilisateurs actifs | | |

Puis répondez : si vous n'aviez regardé que le tableau *Statistics*, qu'auriez-vous conclu dans chacun des deux cas ?

**Mes réponses** (10 visiteurs, 30 s). A : `e["ville"]` au lieu de `e["city"]` dans `recherche_ville`. B : port 8001.

| | Manipulation A | Manipulation B |
|---|---|---|
| L'endpoint concerné est-il dans *Statistics* ? | **Non** : la ligne `/api/events?city=[ville]` a disparu | Seulement `/api/events [init]` |
| Colonne *# Fails* | **0** partout | 10 / 10 (100 %), `ConnectionRefusedError` |
| Onglet *Exceptions* | 25 × `KeyError: 'ville'` | **Vide** |
| Terminal | 25 traces `KeyError: 'ville'` | 10 × `JSONDecodeError`, un par visiteur |
| Compteur d'utilisateurs actifs | 10 du début à la fin | **10 → 0** en 4 s |

- **A** : l'exception survient dans le bloc `catch_response`, donc la requête n'est comptée ni en succès ni en échec : elle **disparaît**. L'erreur est dans une tâche : seule la tâche s'arrête, l'utilisateur survit. Avec *Statistics* seul, on conclurait **« tout va bien, 0 échec »** (code de sortie 0), alors que la recherche par ville n'est plus testée.
- **B** : `response.json()` plante dans `on_start`, et l'utilisateur meurt définitivement, sans être remplacé. Avec *Statistics* seul, on conclurait **« l'API est en panne »**. C'est vrai, mais on ne verrait pas que le test s'est vidé de ses utilisateurs et n'a plus rien mesuré pendant 26 s.

> 0 % d'échecs ne prouve rien tant qu'on n'a pas regardé *Exceptions*, le terminal et le nombre d'utilisateurs actifs.

---

## Exercice 7 — L'organisateur

Pendant une ouverture de ventes, les organisateurs suivent leurs ventes dans le back-office. Ce trafic est rare, mais chaque requête du back-office calcule des statistiques sur toutes les commandes.

**Consignes**

Ajoutez une classe `Organisateur` :

- connectée avec le compte `orga@eventflow.test` / `orga1234` ;
- qui consulte peu souvent : entre 5 et 10 secondes entre deux actions ;
- qui consulte le tableau de bord `GET /api/admin/summary` (poids 1) et les ventes par événement `GET /api/admin/events` (poids 2) ;
- avec des vérifications métier :
  - le tableau de bord n'annonce pas plus d'événements publiés que d'événements ;
  - la liste des ventes n'est pas vide, et aucun événement n'a vendu plus que sa capacité ;
- une proportion d'**un organisateur pour trois visiteurs**.

Ouvrez d'abord les deux URL dans http://localhost:8000/docs (bouton *Authorize* avec le compte organisateur) pour voir le nom exact des champs.

**Observez** (20 utilisateurs, toutes classes)

- Calculez la répartition attendue entre les quatre classes avec leurs `weight`, puis comparez au journal.
- Comparez le temps de réponse de `/api/admin/events` à celui de `/api/events`.

**Bonus — le back-office est-il bien protégé sous charge ?** Ajoutez au `ClientConnecte` une tâche qui vérifie qu'un client **n'a pas** accès à `/api/admin/summary`. Une réponse `403` doit être comptée comme un **succès**, tout autre statut comme un échec. Cette tâche doit apparaître sur sa propre ligne, distincte de celle de l'organisateur.

**Mes réponses**

- **Champs** : `/api/admin/summary` renvoie `{"events", "published", "total_sold", "total_revenue_cents"}` ; `/api/admin/events` renvoie une liste avec `capacity`, `sold`, `revenue_cents`, `fill_rate`.
- **Vérifications** : `published > events` → échec ; liste vide → échec ; `any(e["sold"] > e["capacity"])` → échec. Chacune a été sabotée une fois et a bien échoué avec son message.
- **Répartition** : poids Visiteur 3, Veilleur 1, ClientConnecte 1, Organisateur 1, soit 6 au total. Pour 20 utilisateurs : 20 × 3 ÷ 6 = 10 visiteurs, et 20 ÷ 6 = 3,33 pour chacun des autres. Mesuré : `{"ClientConnecte": 4, "Organisateur": 3, "Veilleur": 3, "Visiteur": 10}` (l'utilisateur restant après l'arrondi va à une classe).
- **Temps de réponse** (20 utilisateurs, 1 minute) : `/api/admin/events` a une médiane de **15 ms**, contre **5 ms** pour `/api/events`, soit 3 fois plus. Le back-office calcule les ventes de chaque événement. Limites : la base ne contient aucune commande (`total_sold: 0`), donc l'écart est sous-estimé ; et il n'y a que 14 requêtes, trop peu pour des percentiles fiables.
- **Bonus** : `response.success()` si le statut vaut 403, `failure` sinon, avec `name="/api/admin/summary [client interdit]"`. Résultat : 0 échec. Sabotage (le client se connecte avec le compte organisateur) : 100 % d'échecs, `HTTP 200`. Le refus prend 4 ms, contre 13 ms pour l'organisateur.

---

## Exercice 8 — Comparer les profils (facultatif)

**Consignes**

En mode headless, lancez **chaque classe seule**, 10 utilisateurs, 30 secondes, statistiques remises à zéro après la montée en charge, avec un export CSV par classe dans un dossier `resultats/`.

**Répondez**

1. Quel endpoint a le temps de réponse médian le plus élevé, toutes classes confondues ?
2. Pour quelle classe les percentiles sont-ils le moins fiables ? Pourquoi ?
3. Quelle classe produit le plus de requêtes par utilisateur ? Est-ce cohérent avec son `wait_time` ?

**Mes réponses** — CSV dans `perf-locust/resultats/` :

```bat
locust --headless -u 10 -r 5 -t 30s --reset-stats --only-summary --csv resultats/visiteur Visiteur
```

Même commande pour `veilleur`/`Veilleur`, `client`/`ClientConnecte` et `organisateur`/`Organisateur`.

| Classe | Requêtes | Médiane globale | p95 global | Endpoint le plus lent (médiane) |
|---|---|---|---|---|
| Visiteur | 153 | 7 ms | 9 ms | `/api/events/[id]`, 8 ms |
| Veilleur | 55 | 4 ms | 8 ms | `/api/health`, 4 ms |
| ClientConnecte | 81 | 5 ms | 9 ms | `/api/auth/token`, 250 ms |
| Organisateur | 42 | 14 ms | 260 ms | `/api/auth/token`, 261 ms |

1. **La médiane la plus élevée** est celle de `POST /api/auth/token`, environ **250 à 260 ms**, 20 à 50 fois plus que les autres : le serveur vérifie le mot de passe avec un calcul volontairement lent. Hors connexion, c'est `/api/admin/events` (14 ms).
   Seulement 5 connexions apparaissent pour 10 utilisateurs : `--reset-stats` a effacé celles des 5 premiers, connectés avant la fin de la montée en charge.
2. **Les percentiles les moins fiables sont ceux de l'`Organisateur`** : 13 requêtes `summary` et 24 `admin/events` seulement, à cause de son attente de 5 à 10 s. Sur 13 valeurs, le p95 est presque la valeur maximale : une seule requête lente suffit à le faire bouger. Son p95 global (260 ms) est aussi tiré vers le haut par les connexions, qui pèsent lourd parmi si peu de requêtes.
3. **Le `Visiteur` produit le plus de requêtes par utilisateur** : environ 15 en 30 s. C'est cohérent avec les `wait_time` :

   | Classe | `wait_time` | Cycle moyen | Attendu en 30 s | Mesuré |
   |---|---|---|---|---|
   | Visiteur | `between(1, 3)` | 2 s | 15 | 15,3 |
   | ClientConnecte | `between(2, 5)` | 3,5 s | 8,6 | 8,1 |
   | Veilleur | `constant_pacing(5)` | 5 s | 6 | 5,5 |
   | Organisateur | `between(5, 10)` | 7,5 s | 4 | 4,2 |

**Remarque** : le `Veilleur` a eu 5 échecs `ConnectionAbortedError` à une mesure, et 0 à la suivante. Ils sont intermittents. Explication probable : le serveur ferme une connexion inactive au bout d'environ 5 s, au moment précis où le veilleur la réutilise, puisqu'il revient toutes les 5 s. C'est un effet du rythme du test, pas une panne de l'API, mais une vraie sonde au même rythme le subirait aussi.

---

## Exercice 9 — Un critère qui ne ment pas

**Consignes**

1. Lancez le test en headless (classe `Visiteur`) contre une API injoignable, en ajoutant `-H http://localhost:8001`. Que dit le bilan ? Que vaut le code de sortie ?
2. Pourquoi ce résultat est-il grave dans un pipeline d'intégration continue ?
3. Rendez le critère fiable. Le test doit échouer :
   - si le p95 global dépasse 300 ms ;
   - si plus de **1 %** des requêtes ont échoué ;
   - s'il n'a exécuté **aucune** requête.
4. Vérifiez les deux situations : API normale → `0` ; port 8001 → `1`.

**Mes réponses**

1. **Bilan avec le critère du cours (p95 seul), port 8001** : `10 requêtes, p95 = 4100 ms, échecs = 100 %`. Une seule ligne, `/api/events [init]`, avec 10 échecs sur 10. Les 10 visiteurs meurent dans `on_start` (`JSONDecodeError` dans le terminal) : il ne reste aucun utilisateur actif.
   **Code de sortie : `1`, mais par coïncidence.** Sous Windows, une connexion refusée met environ 2 s à échouer, donc p95 = 4100 ms > 300 ms. Sous Linux, comme sur un serveur de CI, elle échoue en environ 1 ms : p95 ≈ 1 ms < 300 ms, donc le code serait **`0`**. `process_exit_code` remplace le code par défaut de Locust (1 dès qu'une requête échoue) : notre fonction devient le seul juge.
2. **Pourquoi c'est grave** : le pipeline ne lit que le code de sortie. Avec `0`, il considère le test réussi et continue (fusion, déploiement). On met en production une version **qui n'a pas été testée**, avec une fausse confiance. C'est un **faux positif** (« faux vert ») : pire que pas de test, parce qu'on se croit protégé.
3. **Critère fiable** : trois conditions, dans cet ordre.
   - `num_requests == 0` → `1`. Vérifiée en premier : sans requête, p95 = 0 et échecs = 0 %, donc les deux autres conditions passeraient.
   - `fail_ratio > 0.01` → `1`. Détecte le port 8001 quelle que soit la vitesse des erreurs.
   - `p95 > 300` → `1`.
   - Sinon → `0`.
4. **Vérification** :

   | Situation | Bilan | Code |
   |---|---|---|
   | API normale | 168 requêtes, p95 = 15 ms, 0 % d'échecs | `0` |
   | Port 8001 | 10 requêtes, 100 % d'échecs | `1` |

---

## Exercice 10 — Mission : montée en charge

L'équipe EventFlow veut savoir comment se comporte la consultation du catalogue quand le nombre de visiteurs augmente. À vous de mener la mesure, puis d'en tirer des conclusions argumentées.

**Contraintes**

- uniquement la classe `Visiteur` ;
- quatre paliers : 10, 50, 100 et 200 utilisateurs, une minute chacun ;
- des statistiques qui ne tiennent pas compte de la montée en charge ;
- les résultats de chaque palier conservés en CSV dans `resultats/` ;
- l'utilisation CPU et mémoire des conteneurs observée pendant les mesures ;
- jamais plus de 200 utilisateurs.

**Livrable** — un fichier `ANALYSE.md`, à côté du `locustfile.py`, qui contient :

- un tableau de mesures par palier permettant de comparer le débit attendu et le débit mesuré, la distribution des temps de réponse et le taux d'échecs, globalement et pour les endpoints principaux ;
- une analyse qui répond au moins à ces questions :
  1. Le débit mesuré suit-il le débit théorique ? Sinon, à partir de quand ?
  2. Quel indicateur réagit en premier quand la charge augmente, et que cela suggère-t-il ?
  3. Quel endpoint est le plus coûteux, et l'écart évolue-t-il avec la charge ?
  4. Vos observations permettent-elles de désigner un goulot d'étranglement ?
  5. Un collègue conclut : « EventFlow supporte 200 utilisateurs en production. » Que lui répondez-vous ? Appuyez-vous sur au moins trois limites précises de votre test.

**Pour aller plus loin** — relancez le palier à 50 utilisateurs avec **toutes** les classes. Comparez le p95 global au temps de réponse de `POST /api/auth/token`. Votre critère de réussite aurait-il détecté une connexion trop lente ? Comment le modifieriez-vous ?
