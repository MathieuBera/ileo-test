import requests
from bs4 import BeautifulSoup
import os
import time
import json
import paho.mqtt.publish as publish

BASE_URL = "https://www.mel-ileo.fr"
LOGIN_URL = f"{BASE_URL}/connexion.aspx"
CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"

def ileo_login(session, username, password):
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    viewstate = soup.find(id="__VIEWSTATE")['value']
    eventvalidation = soup.find(id="__EVENTVALIDATION")['value']
    viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")['value']

    payload = {
        '__VIEWSTATE': viewstate,
        '__EVENTVALIDATION': eventvalidation,
        '__VIEWSTATEGENERATOR': viewstategenerator,
        'ctl00$ContentPlaceHolder1$Identifiant': username,
        'ctl00$ContentPlaceHolder1$MotDePasse': password,
        'ctl00$ContentPlaceHolder1$btnConnexion': 'Connexion'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': LOGIN_URL
    }

    login_resp = session.post(LOGIN_URL, data=payload, headers=headers)

    if "Mes consommations" in login_resp.text:
        print("Login réussi")
        return True
    else:
        print("Login échoué")
        print("Page après login :", login_resp.text[:500])
        return False

def get_water_consumption(session):
    resp = session.get(CONSUMPTION_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Exemple d'extraction, à adapter selon la page
    # Cherche un élément avec la conso d'eau
    conso_tag = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_lblConsommation"})
    if conso_tag:
        return conso_tag.text.strip()
    else:
        print("Impossible de trouver la consommation sur la page")
        return None

def publish_mqtt(consommation, mqtt_host, mqtt_port, mqtt_user, mqtt_pass):
    topic = "ileo/eau/consommation"
    payload = json.dumps({"consommation": consommation})

    auth = None
    if mqtt_user and mqtt_pass:
        auth = {'username': mqtt_user, 'password': mqtt_pass}

    publish.single(topic, payload, hostname=mqtt_host, port=mqtt_port, auth=auth)
    print(f"Publié sur MQTT: {payload}")

def main():
    username = os.getenv("ILEO_USER")
    password = os.getenv("ILEO_PASS")

    mqtt_host = os.getenv("MQTT_HOST")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_pass = os.getenv("MQTT_PASS")

    if not username or not password:
        print("Erreur: identifiants ILEO non définis")
        return

    session = requests.Session()
    if not ileo_login(session, username, password):
        return

    consommation = get_water_consumption(session)
    if consommation:
        print("Consommation d'eau:", consommation)
        if mqtt_host:
            publish_mqtt(consommation, mqtt_host, mqtt_port, mqtt_user, mqtt_pass)
        else:
            print("Pas de MQTT configuré, affichage local uniquement")

if __name__ == "__main__":
    main()
