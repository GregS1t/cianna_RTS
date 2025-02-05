import xml.etree.ElementTree as ET
import requests
import base64
from datetime import datetime
import time

from concurrent.futures import ThreadPoolExecutor
import threading
# Importation de la fonction de mise à jour depuis notre module dédié
from cianna_xml_updater import update_cianna_models

SERVER_URL = "http://127.0.0.1:3000"

# URL du fichier XML sur le serveur
URL_MODELS = f"http://127.0.0.1:3000/models/CIANNA_models.xml"

# Chemin local du fichier XML
LOCAL_FILE_MODELS = 'models/CIANNA_models.xml'


def create_xml_param(user_id, ra, dec, h, w, image_path, quantization):
    # Créer la structure XML
    root = ET.Element("YOLO_CIANNA")

    # Ajouter USER_ID
    user_id_elem = ET.SubElement(root, "USER_ID")
    user_id_elem.text = str(user_id)

    # Ajouter Timestamp
    timestamp_elem = ET.SubElement(root, "Timestamp")
    timestamp_elem.text = datetime.now().isoformat()  # Format ISO 8601

    # Ajouter RA, DEC, H, W
    coords_elem = ET.SubElement(root, "Coordinates")
    ET.SubElement(coords_elem, "RA").text = str(ra)
    ET.SubElement(coords_elem, "DEC").text = str(dec)
    ET.SubElement(coords_elem, "H").text = str(h)
    ET.SubElement(coords_elem, "W").text = str(w)

    image_elem = ET.SubElement(root, "Image")
    ET.SubElement(image_elem, "Path").text = image_path

    # Ajouter Quantization
    quantization_elem = ET.SubElement(root, "Quantization")
    quantization_elem.text = str(quantization)

    # Convertir la structure en une chaîne XML
    xml_data = ET.tostring(root, encoding="utf-8", method="xml")        

    print("XML data:", xml_data)
    print(50*".=")
    return xml_data


def send_xml_fits_to_server(xml_data):
    """
        Function to send both the XML and the FITS data to the server
    
    """
    try:
        root = ET.fromstring(xml_data)
        image_path = root.find('Image').find('Path').text
        print("Image path in send_xml_fits_to_server:", image_path)
        if not image_path:
            print("Error: Image path not found in XML data")
            return None
    except ET.ParseError as e:
        print("Error while parsing XML data:", e)
        return None
    
    try:
        with open(image_path, "rb") as fits_file:
            print("FITS file opened successfully")
            files = {
                "xml": ("data.xml", xml_data, "application/xml"),
                "fits": ("image.fits", fits_file, "application/octet-stream")
            }
            response = requests.post(f"{SERVER_URL}/upload", files=files)
    except FileNotFoundError:
        print(f"FITS file not found : {image_path}.")
        return None
    except Exception as e:
        print("Erreur during opening the FITS file:", e)
        return None
    
    if response.status_code == 202:
        process_id = response.json().get("process_id")
        print(f"Processing started with ID: {process_id}")
        return process_id
    else:
        print("Error sending data:", response.text)
        return None

def send_xml_to_server(xml_data):
    """
        Function to send the XML data to the server

        Args:
            xml_data (str): The XML data to send to the server

        Returns:
            str: The process ID if the request was successful, None otherwise
    """

    # XML file transfert
    headers = {'Content-Type': 'application/xml'}
    response = requests.post(f"{SERVER_URL}/upload", data=xml_data, headers=headers)
    
    if response.status_code == 202:
        process_id = response.json().get("process_id")
        print(f"Processing started with ID: {process_id}")
        return process_id
    else:
        print("Error sending XML:", response.text)
        return None
    
def send_image_to_server(image_path):
    """
        Function to send the image data to the server

        Args:
            image_path (str): The path to the image file to send to the server

        Returns:
            str: The process ID if the request was successful, None otherwise
    """

    with open(image_path, "rb") as img_file:
        image_data = base64.b64encode(img_file.read()).decode("utf-8")  # Encodage base64

    headers = {'Content-Type': 'application/json'}
    data = {"image": image_data}
    response = requests.post(f"{SERVER_URL}/upload_image", json=data, headers=headers)
    
    if response.status_code == 202:
        process_id = response.json().get("process_id")
        print(f"Processing started with ID: {process_id}")
        return process_id
    else:
        print("Error sending image:", response.text)
        return None

def poll_for_completion(process_id):
    """
        Function to poll the server for the completion of the process

        Args:
            process_id (str): The process ID to poll for completion

    """
    
    while True:
        response = requests.get(f"{SERVER_URL}/status/{process_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            print(f"Process {process_id} current status: {status}")
            if status == "COMPLETED":
                return True
            elif status == "ERROR":
                print(f"Process {process_id} processing failed!")
                return False
        time.sleep(5)

def download_csv(process_id):
    """
        Function to download the CSV file from the server

        Args:
            process_id (str): The process ID to download the CSV file
    """
    
    response = requests.get(f"{SERVER_URL}/download/{process_id}")
    cvs_file = f"output_{process_id}.csv"
    if response.status_code == 200:
        with open(cvs_file, "wb") as file:
            file.write(response.content)
        print(f"CSV file saved as {cvs_file}")
    else:
        print("Error downloading CSV:", response.text)


def emulate_client_request(request_number: int):
    """
        Function to emulate a request to a server with a a given number
        in the finale version, the requests will be made by the each client
    """
    import random
    # Introduce variability in the parameters of the request
    user_id = 2443423 + request_number
    ra = random.uniform(0, 360)
    dec = random.uniform(-90, 90)
    h = random.randint(50, 200)
    w = random.randint(50, 200)
    image_path = "images/RACS-DR1_0000+12A.fits"  # Chemin vers une image locale
    quantization = 256

    xml_data = create_xml_param(user_id, ra, dec, h, w, image_path, quantization)
    #process_id = send_xml_to_server(xml_data)
    process_id = send_xml_fits_to_server(xml_data)
    if process_id is not None:
        if poll_for_completion(process_id):
            download_csv(process_id)
        else:   
            print(f"Error processing the request: {request_number}")

def main():

    update_result = update_cianna_models(URL_MODELS, LOCAL_FILE_MODELS)
    if update_result is None:
        print("EXIT: Error during XML update.")
        return

    # Emulate multiple clients
    nb_requetes = 3
    with ThreadPoolExecutor(max_workers=nb_requetes) as executor:
        futures = [executor.submit(emulate_client_request, i+1) for i in range(nb_requetes)]
        for future in futures:
            future.result()


if __name__ == '__main__':
    main()