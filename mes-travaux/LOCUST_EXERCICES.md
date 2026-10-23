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
| 10 visiteurs | | |
| 1 veilleur | | — |
| 5 visiteurs sans attente | | |

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

---

## Exercice 8 — Comparer les profils (facultatif)

**Consignes**

En mode headless, lancez **chaque classe seule**, 10 utilisateurs, 30 secondes, statistiques remises à zéro après la montée en charge, avec un export CSV par classe dans un dossier `resultats/`.

**Répondez**

1. Quel endpoint a le temps de réponse médian le plus élevé, toutes classes confondues ?
2. Pour quelle classe les percentiles sont-ils le moins fiables ? Pourquoi ?
3. Quelle classe produit le plus de requêtes par utilisateur ? Est-ce cohérent avec son `wait_time` ?

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
