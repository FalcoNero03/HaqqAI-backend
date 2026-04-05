from google import genai
from dotenv import load_dotenv
from pathlib import Path
import os
import time

load_dotenv(r"C:\Ibra\Projects\vibe coding\API\.env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

"""

STORE_ID = "fileSearchStores/finanzen-3tibtphheqi7"
for datei in ORDNER.iterdir():
    if not datei.is_file():
        continue

    print(f"Hochladen: {datei.name}")

    try:
        operation = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=STORE_ID,
            file=str(datei),
            config={"display_name": datei.name}
        )

        while not operation.done:
            time.sleep(3)
            operation = client.operations.get(operation)

        print(f"Fertig: {datei.name}")

    except Exception as e:
        print(f"Fehler bei {datei.name}: {e}")

print("Upload abgeschlossen.")
"""

"""
file_search_store = client.file_search_stores.create(config={'display_name': 'Satzung'})

operation = client.file_search_stores.upload_to_file_search_store(
    file_search_store_name=file_search_store.name,
        file="mhg_dortmund_satzung.pdf"

)

while not operation.done:
    time.sleep(5)
    operation = client.operations.get(operation)


print(f"Fertig! Store-ID: {file_search_store.name}")  # ← diese Zeile bleibt!
"""


client.file_search_stores.delete(
    name="fileSearchStores/satzung-zofem9s9cwoi",
    config={"force": True}
)
print("Store gelöscht.")

client.file_search_stores.delete(
    name="fileSearchStores/satzung-a0cr2r6ci47n",
    config={"force": True}
)
print("Store gelöscht.")
client.file_search_stores.delete(
    name="fileSearchStores/satzung-64ddks7nm97h",
    config={"force": True}
)
print("Store gelöscht.")
client.file_search_stores.delete(
    name="fileSearchStores/satzung-60c0r4cyfj7u",
    config={"force": True}
)
print("Store gelöscht.")



print("Vorhandene Stores:")
for store in client.file_search_stores.list():
    print(store.name, "-", getattr(store, "display_name", ""))

     