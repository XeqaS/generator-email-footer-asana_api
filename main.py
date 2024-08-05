import asana
from dotenv import load_dotenv
import os
import json
from jinja2 import Environment, FileSystemLoader
from unidecode import unidecode
import requests

# Załaduj zmienne środowiskowe z pliku .env
load_dotenv()

# Uzyskaj token API i ID projektu z zmiennych środowiskowych
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PROJECT_ID = os.getenv('PROJECT_ID')

# Ustawienie nagłówka autoryzacji
configuration = asana.Configuration()
configuration.access_token = ACCESS_TOKEN

# Inicjalizacja klienta API
client = asana.ApiClient(configuration=configuration)

# Pobieranie listy zadań z projektu, filtrując tylko nieukończone zadania
tasks_api = asana.TasksApi(client)
tasks = tasks_api.get_tasks_for_project(PROJECT_ID, opts={'opt_fields': 'completed'})

# Utwórz folder 'json', jeśli nie istnieje
json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json')
os.makedirs(json_dir, exist_ok=True)

# Utwórz folder 'wygenerowane', jeśli nie istnieje
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wygenerowane')
os.makedirs(output_dir, exist_ok=True)

# Ustawienia Jinja2
env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))
template_zdjecie = env.get_template('szablon_zdjecie.html')
template_bez_zdjecia = env.get_template('szablon_bez_zdjecia.html')

# Przetwarzanie każdego zadania w projekcie
for task in tasks:
    if task['completed']:
        continue  # Pomijamy ukończone zadania
    
    task_id = task['gid']
    task_details = tasks_api.get_task(task_id, opts={'opt_fields': 'name,notes,created_by'})

    task_name = task_details['name']
    ID_creator = task_details['created_by']['gid']

    # Filtracja zadań, aby przetwarzać tylko te z "Stopka" w tytule
    if "STOPKA" in task_name:
        task_notes = task_details.get('notes', '')

        # Podział notatek na linie
        task_lines = task_notes.splitlines()

        # Przypisywanie linii do zmiennych
        if len(task_lines) >= 5:  # Upewnij się, że masz co najmniej 5 linii
            imie, nazwisko = task_lines[0].split(maxsplit=1)
            stan = task_lines[1]
            woj = task_lines[2]
            tel = task_lines[3]
            wersja = task_lines[4]
        else:
            imie = nazwisko = stan = woj = tel = wersja = "Brak danych"

        print(f"Task name: {task_name}")
        print(f"Task notes: {task_notes}")
        print(f"ID Creator: {ID_creator}\n")

        # Wyświetlanie zmiennych
        print(f"Imie: {imie}")
        print(f"Nazwisko: {nazwisko}")
        print(f"Stan: {stan}")
        print(f"Woj: {woj}")
        print(f"Tel: {tel}")
        print(f"Wersja: {wersja}\n")

        # Zapis danych do pliku JSON
        task_data = {
            "task_id": task_id,
            "task_name": task_name,
            "ID_creator": ID_creator,
            "imie": imie,
            "nazwisko": nazwisko,
            "stan": stan,
            "woj": woj,
            "tel": tel,
            "wersja": wersja
        }

        json_filename = os.path.join(json_dir, f'task_{task_id}.json')
        with open(json_filename, 'w') as json_file:
            json.dump(task_data, json_file, indent=4)

def process_task_file(filename):
    # Wczytywanie danych z pliku JSON
    with open(filename, 'r', encoding='utf-8') as json_file:
        task_data = json.load(json_file)

    # Pobieranie danych z pliku JSON
    task_id = task_data['task_id']
    imie = task_data['imie']
    nazwisko = task_data['nazwisko']
    stan = task_data['stan']
    woj = task_data['woj']
    tel = task_data['tel']
    wersja = task_data.get('wersja', 'nie')  # Pobranie wersji, domyślnie 'nie'

    # Tworzenie zmiennej tel_link (bez spacji)
    tel_link = tel.replace(" ", "")

    # Tworzenie zmiennej zdj (połączenie imie i nazwisko bez polskich znaków)
    zdj = unidecode(imie + nazwisko)

    # Tworzenie zmiennej mail (połączenie imie i nazwisko z kropką pomiędzy)
    mail = f"{unidecode(imie).lower()}.{unidecode(nazwisko).lower()}"

    # Wybór szablonu na podstawie wartości zmiennej wersja
    if wersja.lower() == "nie":
        template = template_bez_zdjecia
    else:
        template = template_zdjecie

    # Renderowanie szablonu
    rendered_html = template.render(
        imie=imie,
        nazwisko=nazwisko,
        stan=stan,
        woj=woj,
        tel=tel,
        tel_link=tel_link,
        zdj=zdj,
        mail=mail
    )

    # Tworzenie nazwy pliku na podstawie imienia i nazwiska
    output_filename = os.path.join(output_dir, f'{unidecode(imie)}{unidecode(nazwisko)}.html')

    # Zapisywanie wygenerowanego HTML do pliku
    with open(output_filename, 'w', encoding='utf-8') as output_file:
        output_file.write(rendered_html)

    print(f'Generated file: {output_filename}')

    # Dodanie wygenerowanego pliku HTML jako załącznika do zadania w Asana
    try:
        with open(output_filename, 'rb') as file_content:
            response = requests.post(
                f'https://app.asana.com/api/1.0/tasks/{task_id}/attachments',
                headers={
                    'Authorization': f'Bearer {ACCESS_TOKEN}'
                },
                files={
                    'file': (output_filename.encode('utf-8'), file_content, 'text/html')
                }
            )
        if response.status_code == 200:
            print(f'Added attachment to task {task_id}')
        else:
            print(f'Failed to add attachment to task {task_id}: {response.text}')
    except Exception as e:
        print(f'Failed to add attachment to task {task_id}: {e}')

# Przetwarzanie wszystkich plików JSON w folderze 'json'
for filename in os.listdir(json_dir):
    if filename.startswith('task_') and filename.endswith('.json'):
        process_task_file(os.path.join(json_dir, filename))