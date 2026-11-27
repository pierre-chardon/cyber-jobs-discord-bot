"""
Bot d'offres cyber pour Discord.

Toutes les 30 minutes, cherche les nouvelles offres en cybersecurite et en
architecture / ingenierie reseau, puis les publie dans un salon Discord via un
webhook. Les offres deja vues sont memorisees dans deja_publiees.json.

Sources (chacune s'active si ses cles sont definies) :
  - pages carriere Lever et Greenhouse (voir entreprises.json), toujours actives
  - Adzuna (agregateur)        : ADZUNA_APP_ID et ADZUNA_APP_KEY
  - Jooble (agregateur)        : JOOBLE_KEY (100 recherches par jour : 3 recherches
                                 une fois par heure, soit 72 par jour)
  - Adzuna est payant : laisser ses cles vides pour le desactiver
  - France Travail             : FT_CLIENT_ID et FT_CLIENT_SECRET

Variables d'environnement :
  DISCORD_WEBHOOK    adresse du webhook du salon Discord (obligatoire)
  ZONE               zone de recherche des agregateurs (defaut "France" ;
                     "Ile-de-France" pour limiter a la region)
  FT_REGION          code region France Travail (11 = Ile-de-France)
  MAX_OFFRES         nombre maximum d'offres publiees par passage (defaut 10)
  DRY_RUN            "1" pour afficher les offres sans rien publier ni memoriser
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

FICHIER_ENTREPRISES = "entreprises.json"
FICHIER_MEMOIRE = "deja_publiees.json"
OUBLI_JOURS = 60  # on oublie les offres vues il y a plus de 60 jours
COULEUR = 0x5CC8E6
ENTETES = {"User-Agent": "bot-offres-cyber-discord/1.0"}

# Intitules lies a la cyber ou aux reseaux (francais et anglais).
FILTRE_INTITULE = re.compile(
    r"cyber|security|s[ée]curit[ée] (informatique|des syst|si\b|r[ée]seau|op[ée]rationnelle|it\b)"
    r"|\bsoc\b|secops|pentest|penetration|test d.intrusion|siem|\bgrc\b|rssi|ciso|"
    r"threat|forensic|vuln[ée]rabilit|\bcti\b|\bssi\b|purple|blue team|red team|"
    r"(ing[ée]nieur|architecte|administrateur|technicien|engineer|architect|admin)\w*"
    r"[^,;]{0,25}(r[ée]seau|network)|network (engineer|architect|admin)",
    re.IGNORECASE,
)

# Recherches envoyees aux agregateurs (une requete par ligne).
RECHERCHES_ADZUNA = [
    {"what_or": "cybersécurité cybersecurity pentest pentester SOC SIEM RSSI"},
    {"what": "sécurité informatique"},
    {"what": "architecte réseau"},
    {"what": "ingénieur réseau"},
]
RECHERCHES_JOOBLE = ["cybersécurité", "sécurité informatique", "ingénieur réseau"]

# Lieux acceptes pour les offres des entreprises (France ou teletravail).
FILTRE_LIEU = re.compile(
    r"france|paris|[iî]le-de-france|lyon|lille|nantes|rennes|toulouse|bordeaux|"
    r"marseille|montpellier|grenoble|sophia|nice|strasbourg|remote|t[ée]l[ée]travail",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- utilitaires

def env(nom, defaut=None):
    return os.environ.get(nom, defaut)


def get_json(urls):
    """Essaie chaque adresse et renvoie le premier JSON obtenu, sinon None."""
    for url in urls:
        try:
            reponse = requests.get(url, headers=ENTETES, timeout=30)
        except requests.RequestException as erreur:
            print(f"  {url} : {erreur}")
            continue
        if reponse.status_code == 200:
            return reponse.json()
        print(f"  {url} : code {reponse.status_code}")
    return None


def charger_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut


def sauver_memoire(memoire):
    limite = (datetime.now(timezone.utc) - timedelta(days=OUBLI_JOURS)).isoformat()
    memoire = {k: v for k, v in memoire.items() if v >= limite}
    with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
        json.dump(memoire, f, indent=0, sort_keys=True)


def offre(cle, titre, lien, entreprise, lieu, contrat, date, source):
    return {
        "cle": cle, "titre": titre, "lien": lien, "entreprise": entreprise,
        "lieu": lieu or "Non précisé", "contrat": contrat or "Non précisé",
        "date": date, "source": source,
    }


# ---------------------------------------------------------------- sources

def depuis_lever(slug, nom):
    donnees = get_json([
        f"https://api.lever.co/v0/postings/{slug}?mode=json",
        f"https://api.eu.lever.co/v0/postings/{slug}?mode=json",
    ])
    resultats = []
    for p in donnees or []:
        cat = p.get("categories") or {}
        lieu = cat.get("location") or ""
        date = None
        if p.get("createdAt"):
            date = datetime.fromtimestamp(p["createdAt"] / 1000, timezone.utc).isoformat()
        resultats.append(offre(
            f"lever:{slug}:{p['id']}", p.get("text", ""), p.get("hostedUrl"),
            nom, lieu, cat.get("commitment"), date, "Lever"))
    return resultats


def depuis_greenhouse(token, nom):
    donnees = get_json([
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
        f"https://boards-api.eu.greenhouse.io/v1/boards/{token}/jobs",
    ])
    resultats = []
    for j in (donnees or {}).get("jobs", []):
        lieu = (j.get("location") or {}).get("name") or ""
        resultats.append(offre(
            f"greenhouse:{token}:{j['id']}", j.get("title", ""), j.get("absolute_url"),
            nom, lieu, None, j.get("updated_at"), "Greenhouse"))
    return resultats


def depuis_france_travail(client_id, client_secret, region):
    jeton = requests.post(
        "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
        params={"realm": "/partenaire"},
        data={"grant_type": "client_credentials", "client_id": client_id,
              "client_secret": client_secret, "scope": "api_offresdemploiv2 o2dsoffre"},
        timeout=30,
    )
    jeton.raise_for_status()
    token = jeton.json()["access_token"]
    fin = datetime.now(timezone.utc).replace(microsecond=0)
    debut = fin - timedelta(hours=48)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    resultats = []
    for mot in ["cybersecurite", "securite informatique", "SOC", "pentest", "SIEM", "RSSI"]:
        params = {"motsCles": mot, "minCreationDate": debut.strftime(fmt),
                  "maxCreationDate": fin.strftime(fmt), "range": "0-149"}
        if region:
            params["region"] = region
        r = requests.get(
            "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
            params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if r.status_code in (200, 206):
            for o in r.json().get("resultats", []):
                lien = (o.get("origineOffre") or {}).get("urlOrigine") or \
                    f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}"
                contrat = o.get("typeContratLibelle") or o.get("typeContrat")
                if o.get("alternance"):
                    contrat = f"{contrat} · Alternance"
                resultats.append(offre(
                    f"ft:{o['id']}", o.get("intitule", ""), lien,
                    (o.get("entreprise") or {}).get("nom") or "Non précisée",
                    (o.get("lieuTravail") or {}).get("libelle"), contrat,
                    o.get("dateCreation"), "France Travail"))
        time.sleep(0.5)
    return resultats


def depuis_adzuna(app_id, app_key, zone):
    resultats = []
    for recherche in RECHERCHES_ADZUNA:
        params = {"app_id": app_id, "app_key": app_key, "results_per_page": 50,
                  "max_days_old": 2, "sort_by": "date", "content-type": "application/json"}
        params.update(recherche)
        if zone and zone.lower() != "france":
            params["where"] = zone
        try:
            r = requests.get("https://api.adzuna.com/v1/api/jobs/fr/search/1",
                             params=params, headers=ENTETES, timeout=30)
        except requests.RequestException as erreur:
            print(f"  Adzuna : {erreur}")
            continue
        if r.status_code != 200:
            print(f"  Adzuna {recherche} : code {r.status_code} {r.text[:150]}")
            continue
        for j in r.json().get("results", []):
            contrat = {"permanent": "CDI", "contract": "CDD / mission"}.get(
                j.get("contract_type"), j.get("contract_type"))
            resultats.append(offre(
                f"adzuna:{j['id']}", j.get("title", ""), j.get("redirect_url"),
                (j.get("company") or {}).get("display_name") or "Non précisée",
                (j.get("location") or {}).get("display_name"), contrat,
                j.get("created"), "Adzuna"))
        time.sleep(1)
    return resultats


def depuis_jooble(cle, zone):
    resultats = []
    for mots in RECHERCHES_JOOBLE:
        corps = {"keywords": mots, "location": zone or "France", "ResultOnPage": 50}
        donnees = None
        for domaine in ("fr.jooble.org", "jooble.org"):
            try:
                r = requests.post(f"https://{domaine}/api/{cle}", json=corps,
                                  headers=ENTETES, timeout=30)
            except requests.RequestException as erreur:
                print(f"  Jooble : {erreur}")
                continue
            if r.status_code == 200:
                donnees = r.json()
                break
            print(f"  Jooble ({domaine}) : code {r.status_code}")
        for j in (donnees or {}).get("jobs", []):
            resultats.append(offre(
                f"jooble:{j.get('id')}", j.get("title", ""), j.get("link"),
                j.get("company") or "Non précisée", j.get("location"), j.get("type"),
                j.get("updated"), "Jooble"))
    return resultats


def signature(o):
    """Meme offre vue sur deux sites : meme intitule et meme entreprise."""
    norm = lambda t: re.sub(r"\W+", " ", (t or "").lower()).strip()
    return f"{norm(o['titre'])}|{norm(o['entreprise'])}"


# ---------------------------------------------------------------- Discord

def en_embed(o):
    embed = {
        "title": o["titre"][:256],
        "url": o["lien"],
        "color": COULEUR,
        "fields": [
            {"name": "Entreprise", "value": o["entreprise"][:1024], "inline": True},
            {"name": "Lieu", "value": o["lieu"][:1024], "inline": True},
            {"name": "Contrat", "value": o["contrat"][:1024], "inline": True},
        ],
        "footer": {"text": f"Source : {o['source']}"},
    }
    if o.get("date"):
        embed["timestamp"] = o["date"]
    return embed


def envoyer(webhook, payload):
    reponse = requests.post(webhook, json=payload, timeout=30)
    if reponse.status_code == 429:
        time.sleep(float(reponse.json().get("retry_after", 5)))
        reponse = requests.post(webhook, json=payload, timeout=30)
    reponse.raise_for_status()
    time.sleep(2)


def publier(webhook, embeds):
    for i in range(0, len(embeds), 10):  # 10 cartes maximum par message
        envoyer(webhook, {"username": "Offres cyber", "embeds": embeds[i:i + 10]})


# ---------------------------------------------------------------- programme

def main():
    dry_run = env("DRY_RUN", "0") == "1"
    webhook = env("DISCORD_WEBHOOK")
    if not webhook and not dry_run:
        sys.exit("Variable manquante : DISCORD_WEBHOOK")
    max_offres = int(env("MAX_OFFRES", "10"))

    entreprises = charger_json(FICHIER_ENTREPRISES, {})
    premiere_fois = not os.path.exists(FICHIER_MEMOIRE)
    memoire = charger_json(FICHIER_MEMOIRE, {})

    toutes = []
    for slug, nom in entreprises.get("lever", {}).items():
        print(f"Lever : {nom}")
        toutes += [o for o in depuis_lever(slug, nom) if FILTRE_LIEU.search(o["lieu"])]
    for token, nom in entreprises.get("greenhouse", {}).items():
        print(f"Greenhouse : {nom}")
        toutes += [o for o in depuis_greenhouse(token, nom) if FILTRE_LIEU.search(o["lieu"])]
    zone = env("ZONE", "France")
    if env("ADZUNA_APP_ID") and env("ADZUNA_APP_KEY"):
        print("Adzuna")
        toutes += depuis_adzuna(env("ADZUNA_APP_ID"), env("ADZUNA_APP_KEY"), zone)
    # Jooble : une fois par heure seulement (passage de la premiere demi-heure),
    # pour rester sous la limite gratuite de 100 recherches par jour.
    if env("JOOBLE_KEY") and (datetime.now(timezone.utc).minute < 30 or premiere_fois):
        print("Jooble")
        toutes += depuis_jooble(env("JOOBLE_KEY"), zone)
    if env("FT_CLIENT_ID") and env("FT_CLIENT_SECRET"):
        print("France Travail")
        try:
            toutes += depuis_france_travail(env("FT_CLIENT_ID"), env("FT_CLIENT_SECRET"),
                                            env("FT_REGION", "11"))
        except requests.RequestException as erreur:
            print(f"  France Travail indisponible : {erreur}")

    cyber = {o["cle"]: o for o in toutes if FILTRE_INTITULE.search(o["titre"])}
    # On ecarte aussi une offre deja publiee sous un autre site (meme intitule et entreprise).
    vues = {cle for cle in memoire if cle.startswith("sig:")}
    nouvelles, signatures = [], set()
    for cle, o in cyber.items():
        sig = "sig:" + signature(o)
        if cle in memoire or sig in vues or sig in signatures:
            memoire.setdefault(cle, datetime.now(timezone.utc).isoformat())
            continue
        signatures.add(sig)
        nouvelles.append(o)
    print(f"{len(cyber)} offre(s) cyber suivie(s), dont {len(nouvelles)} nouvelle(s).")

    if dry_run:
        for o in nouvelles:
            print(f"- {o['titre']} | {o['entreprise']} | {o['lieu']} | {o['lien']}")
        return

    maintenant = datetime.now(timezone.utc).isoformat()

    if premiere_fois:
        # Premier passage : on memorise les offres existantes sans les publier,
        # pour ne pas inonder le salon, et on annonce que le bot est en place.
        for cle, o in cyber.items():
            memoire[cle] = maintenant
            memoire["sig:" + signature(o)] = maintenant
        sauver_memoire(memoire)
        envoyer(webhook, {"username": "Offres cyber", "content":
                f"✅ Bot d'offres en place : {len(cyber)} offre(s) cyber et réseau actuellement "
                "suivie(s). Les nouvelles offres seront publiées ici dès leur mise en ligne."})
        return

    if not nouvelles:
        sauver_memoire(memoire)
        return

    nouvelles.sort(key=lambda o: o.get("date") or "")
    a_publier = nouvelles[-max_offres:]
    publier(webhook, [en_embed(o) for o in a_publier])
    for o in nouvelles:  # memorise aussi celles ecartees par la limite
        memoire[o["cle"]] = maintenant
        memoire["sig:" + signature(o)] = maintenant
    sauver_memoire(memoire)


if __name__ == "__main__":
    main()
