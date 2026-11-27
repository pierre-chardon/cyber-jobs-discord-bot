"""Test ponctuel : quelle zone Jooble donne des offres en Suisse ? (3 appels)"""
import os
import requests

cle = os.environ["JOOBLE_KEY_CH"]
for zone in ["Suisse", "Schweiz", "Switzerland"]:
    corps = {"keywords": "cyber security", "location": zone, "ResultOnPage": 5}
    r = requests.post(f"https://ch.jooble.org/api/{cle}", json=corps, timeout=30)
    if r.status_code != 200:
        print(f"{zone:12} : erreur {r.status_code}")
        continue
    donnees = r.json()
    lieux = sorted({j.get("location", "?") for j in donnees.get("jobs", [])})
    print(f"{zone:12} : {donnees.get('totalCount', 0)} offres  | exemples de lieux : {', '.join(lieux)}")
