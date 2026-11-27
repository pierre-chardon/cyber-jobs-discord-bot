"""Test ponctuel : sur quel site Jooble la cle fonctionne-t-elle ? (3 appels)"""
import os
import requests

cle = os.environ["JOOBLE_KEY_CH"].strip()
print(f"Longueur de la cle : {len(cle)} caracteres")
for domaine in ["ch.jooble.org", "jooble.org", "fr.jooble.org"]:
    corps = {"keywords": "cyber security", "location": "Schweiz", "ResultOnPage": 5}
    r = requests.post(f"https://{domaine}/api/{cle}", json=corps, timeout=30)
    if r.status_code != 200:
        print(f"{domaine:15} : erreur {r.status_code}")
        continue
    donnees = r.json()
    lieux = sorted({j.get("location", "?") for j in donnees.get("jobs", [])})
    print(f"{domaine:15} : {donnees.get('totalCount', 0)} offres | lieux : {', '.join(lieux)}")
