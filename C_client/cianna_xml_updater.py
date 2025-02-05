import requests
import xml.etree.ElementTree as ET
import os

def get_last_update(xml_content):
    """
    Extrait la valeur de la balise <LastUpdate> dans le contenu XML.
    """
    try:
        root = ET.fromstring(xml_content)
        last_update_elem = root.find('LastUpdate')
        if last_update_elem is not None:
            return last_update_elem.text.strip()
    except ET.ParseError as e:
        print("Erreur lors de l'analyse du XML :", e)
    return None

def download_xml(url):
    """
    Télécharge le contenu XML depuis l'URL indiquée.
    """
    try:
        print("URL : {}".format(url))
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print("Erreur lors du téléchargement :", e)
        return None

def update_cianna_models(url, local_file):
    """
    Télécharge le fichier XML des modèles depuis le serveur et le compare avec le fichier local.
    Si le fichier distant a une date de mise à jour différente, il remplace le fichier local.
    
    Retourne :
      - True si le fichier local a été mis à jour ou téléchargé pour la première fois,
      - False si le fichier local est déjà à jour,
      - None en cas d'erreur.
    """
    remote_xml = download_xml(url)
    if remote_xml is None:
        print("Le téléchargement du fichier distant a échoué.")
        return None

    remote_last_update = get_last_update(remote_xml)
    if not remote_last_update:
        print("Impossible d'extraire la balise <LastUpdate> du fichier distant.")
        return None

    if os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf-8') as f:
            local_xml = f.read()
        local_last_update = get_last_update(local_xml)

        if local_last_update != remote_last_update:
            with open(local_file, 'w', encoding='utf-8') as f:
                f.write(remote_xml)
            print("Le fichier local a été mis à jour avec la version la plus récente.")
            return True
        else:
            print("Le fichier local est déjà à jour.")
            return False
    else:
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(remote_xml)
        print("Le fichier distant a été téléchargé et sauvegardé localement.")
        return True