from google import genai
from google.genai import types
from dotenv import load_dotenv
import os


def print_sources(response):
    print("\nQuellen:")
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks
        if chunks:
            seen = set()
            for chunk in chunks:
                title = chunk.retrieved_context.title
                if title and title not in seen:
                    seen.add(title)
                    print(f"- {title}")
        else:
            print("(Keine Quellen gefunden)")
    except Exception:
        print("(Quellenangabe nicht verfuegbar)")


load_dotenv(r"C:\Ibra\Projects\vibe coding\API\.env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Alle Store-IDs auslesen
store_ids = []
for key, value in os.environ.items():
    if key.startswith("FILE_SEARCH_STORE_") and value.startswith("fileSearchStores/"):
        store_ids.append(value)

if not store_ids:
    raise ValueError("Keine FILE_SEARCH_STORE_* Einträge in .env gefunden.")

print(f"Geladene Stores ({len(store_ids)}): {store_ids}\n")

# Natives Gemini Chat-Format
history = []

print("Chat gestartet. Zum Beenden: exit, quit oder q\n")

while True:
    question = input("Frage: ").strip()

    if question.lower() in {"exit", "quit", "q"}:
        print("Chat beendet.")
        break

    if not question:
        print("Bitte gib eine Frage ein.")
        continue

    # Frage zum Verlauf hinzufügen (natives Format)
    history.append(types.Content(
        role="user",
        parts=[types.Part(text=question)]
    ))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction="""
Du bist ein hilfreicher Assistent mit Zugriff auf mehrere Wissensdokumente.

Regeln:
- Nutze alle bereitgestellten Wissensquellen und wähle die relevantesten Informationen aus.
- Wenn mehrere Quellen relevant sind, kombiniere sie sinnvoll.
- Wenn die Frage finanzielle Regeln betrifft, achte besonders auf Finanzdokumente.
- Wenn die Frage Satzung, Struktur oder Zuständigkeiten betrifft, achte auf Satzungsdokumente.
- Wenn die Frage Vorgehensweisen oder praktische Umsetzung betrifft, achte auf Anleitungen.
- Beantworte Fragen verständlich und natürlich.
- Wenn die Quellen keine klare Antwort geben, sage das offen.
- Erfinde keine Inhalte außerhalb der Quellen.
""",
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=store_ids  # alle Stores
                    )
                )
            ],
        ),
    )

    answer = response.text or "(Keine Antwort erhalten)"

    # Antwort zum Verlauf hinzufügen
    history.append(types.Content(
        role="model",
        parts=[types.Part(text=answer)]
    ))

    print(f"\nAntwort:\n{answer}")
    print_sources(response)
    print()