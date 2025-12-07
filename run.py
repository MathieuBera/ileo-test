import os
import time
import requests
from bs4 import BeautifulSoup
import paho.mqtt.publish as publish

ILEO_USER = os.getenv('ILEO_USER')
ILEO_PASS = os.getenv('ILEO_PASS')
PUBLISH_METHOD = os.getenv('PUBLISH_METHOD', 'mqtt')
MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASS = os.getenv('MQTT_PASS')
HA_URL = os.getenv('HA_URL')
HA_TOKEN = os.getenv('HA_TOKEN')

SESSION = requests.Session()

def login():
    login_url = 'https://www.mel-ileo.fr/connexion.aspx'
    r = SESSION.get(login_url, timeout=30)
    soup = BeautifulSoup(r.text, 'html.parser')
    # Ici il faudra peut-être récupérer des tokens __VIEWSTATE etc. si présents dans le formulaire
    payload = {
        'Identifiant': ILEO_USER,
        'Motdepasse': ILEO_PASS
    }
    try:
        resp = SESSION.post(login_url, data=payload, timeout=30)
        resp.raise_for_status()
        # Vérifier succès login, par ex. présence d'un élément spécifique ou URL de redirection
        if "mes-consommations" not in resp.text:
            print("Login may have failed, check credentials or form fields")
            return False
        return True
    except Exception as e:
        print('Login failed:', e)
        return False

def fetch_consumption():
    url = 'https://www.mel-ileo.fr/espaceperso/mes-consommations.aspx'
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Exemple : cherche un élément CSS avec classe 'current-consumption'
    el = soup.select_one('.current-consumption')
    if el:
        return el.get_text(strip=True)

    # Sinon essaie d'extraire un JSON embedded ou autre selon la page
    return None

def publish_mqtt(value):
    if not MQTT_HOST or not value:
        print("MQTT publish skipped (missing host or value)")
        return
    auth = None
    if MQTT_USER:
        auth = {'username': MQTT_USER, 'password': MQTT_PASS}
    publish.single('homeassistant/sensor/ileo_conso/state', payload=str(value), hostname=MQTT_HOST, port=MQTT_PORT, auth=auth)
    print('Published MQTT:', value)

def publish_rest(value):
    if not HA_URL or not HA_TOKEN or not value:
        print("REST publish skipped (missing URL, token or value)")
        return
    url = f"{HA_URL.rstrip('/')}/api/states/sensor.ileo_conso"
    headers = {'Authorization': f'Bearer {HA_TOKEN}', 'Content-Type': 'application/json'}
    payload = {
        'state': str(value),
        'attributes': {
            'friendly_name': 'ILEO consommation',
            'unit_of_measurement': 'L',
        }
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    print('REST publish:', resp.status_code, resp.text)

if __name__ == '__main__':
    ok = login()
    if not ok:
        print('Login failed — abort')
        raise SystemExit(1)

    val = fetch_consumption()
    if not val:
        print('No consumption value found — abort')
        raise SystemExit(1)

    if PUBLISH_METHOD == 'mqtt':
        publish_mqtt(val)
    else:
        publish_rest(val)

    print('Run complete')
