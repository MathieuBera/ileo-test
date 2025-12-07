import requests
from bs4 import BeautifulSoup
import os
import json

BASE_URL = "https://www.mel-ileo.fr"
LOGIN_URL = f"{BASE_URL}/connexion.aspx"
CONSUMPTION_URL = f"{BASE_URL}/espaceperso/mes-consommations.aspx"

def save_to_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Contenu sauvegardé dans {filename}")

def ileo_login(session, username, password):
    print("=== GET page login ===")
    resp = session.get(LOGIN_URL)
    print(f"GET {LOGIN_URL} status: {resp.status_code}")
    save_to_file("login_page.html", resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    viewstate = soup.find(id="__VIEWSTATE")['value'] if soup.find(id="__VIEWSTATE") else None
    eventvalidation = soup.find(id="__EVENTVALIDATION")['value'] if soup.find(id="__EVENTVALIDATION") else None
    viewstategenerator = soup.find(id="__VIEWSTATEGENERATOR")['value'] if soup.find(id="__VIEWSTATEGENERATOR") else None

    print(f"__VIEWSTATE length: {len(viewstate) if viewstate else 'absent'}")
    print(f"__EVENTVALIDATION length: {len(eventvalidation) if eventvalidation else 'absent'}")
    print(f"__VIEWSTATEGENERATOR length: {len(viewstategenerator) if viewstategenerator else 'absent'}")

    payload = {
        '__VIEWSTATE': viewstate or '',
        '__EVENTVALIDATION': eventvalidation or '',
        '__VIEWSTATEGENERATOR': viewstategenerator or '',
        'ctl00$ContentPlaceHolder1$Identifiant': username,
        'ctl00$ContentPlaceHolder1$MotDePasse': password,
        'ctl00$ContentPlaceHolder1$btnConnexion': 'Connexion'
    }
    print("Payload login (sans mot de passe) :", {k: v if k != 'ctl00$ContentPlaceHolder1$MotDePasse' else '***' for k,v in payload.items()})

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': LOGIN_URL
    }

    print("=== POST page login ===")
    login_resp = session.post(LOGIN_URL, data=payload, headers=headers)
    print(f"POST {LOGIN_URL} status: {login_resp.status_code}")
    print(f"URL après login : {login_resp.url}")
    print("Cookies après login :", session.cookies.get_dict())
    save_to_file("post_login_page.html", login_resp.text)

    # Affiche les 2000 premiers caractères pour debug rapide
    print("Début réponse POST login (2000 premiers caractères) :")
    print(login_resp.text[:2000])

    if "Mes consommations" in login_resp.text:
        print("Login réussi")
        return True
    else:
        print("Login échoué")
        return False

def get_water_consumption(session):
    print("Récupération de la page consommation...")
    resp = session.get(CONSUMPTION_URL)
    print(f"GET {CONSUMPTION_URL} status: {resp.status_code}")
    save_to_file("consumption_page.html", resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")

    conso_tag = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_lblConsommation"})
    if conso_tag:
        return conso_tag.text.strip()
    else:
        print("Impossible de trouver la consommation sur la page")
        return None

def main():
    print("Début du script ILEO Scraper - logs très détaillés")

    username = os.getenv("ILEO_USER")
    password = os.getenv("ILEO_PASS")

    if not username or not password:
        print("Erreur: identifiants ILEO non définis")
        return

    session = requests.Session()
    if not ileo_login(session, username, password):
        print("Abandon, login impossible")
        return

    consommation = get_water_consumption(session)
    if consommation:
        print("Consommation d'eau:", consommation)
    else:
        print("Pas de consommation trouvée")

if __name__ == "__main__":
    main()
