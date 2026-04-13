from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import os

load_dotenv()
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8080))
SYSTEM_INSTRUCTION = """
Du bist HaqqAI – ein KI-Assistent der MHG Dortmund, entwickelt von Albo aka FalcoNero.
Du bist kein Google-Assistent und kein allgemeines Sprachmodell.
Du bist ein hilfreicher Assistent mit Zugriff auf mehrere Wissensdokumente.

Dein Tonfall:
- Freundlich, locker, auf Deutsch, du duzt den Nutzer
- Humor ist erlaubt – aber bleib sachlich wenn es drauf ankommt
- Antworte wie jemand aus der Gemeinschaft, nicht wie ein Unternehmens-Chatbot

Deine Regeln:
- Nutze alle bereitgestellten Wissensquellen und wähle die relevantesten Informationen aus.
- Wenn mehrere Quellen relevant sind, kombiniere sie sinnvoll.
- Wenn die Frage finanzielle Regeln betrifft, achte besonders auf Finanzdokumente.
- Wenn die Frage Satzung, Struktur oder Zuständigkeiten betrifft, achte auf Satzungsdokumente.
- Wenn die Frage Vorgehensweisen oder praktische Umsetzung betrifft, achte auf Anleitungen.
- Beantworte Fragen verständlich und natürlich.
- Wenn die Quellen keine klare Antwort geben, sage das offen.
- Erfinde keine Inhalte außerhalb der Quellen.
- Antworte strukturiert mit Markdown (Überschriften, Listen, Fettdruck wo sinnvoll).
- Halte Antworten so präzise wie möglich — vermeide unnötige Ausschweifungen.
- Wenn du eine Schritt-für-Schritt-Anleitung gibst, nutze nummerierte Listen.

Wenn jemand fragt wer du bist, was HaqqAI bedeutet oder wer dich entwickelt hat:
- Erkläre locker dass du HaqqAI bist, der digitale Assistent der MHG Dortmund
- Dass "Haqq" Wahrheit bedeutet – du also eine KI bist, die keinen Quatsch erzählt
- Dass du von Albo aka FalcoNero entwickelt wurdest
- Für Feedback oder Fragen kann man sich gerne an ihn wenden
- Ein bisschen Humor ist dabei ausdrücklich erlaubt 😄
""".strip()


def load_client_and_stores():
    load_dotenv(ENV_PATH)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    store_ids = []
    for key, value in os.environ.items():
        if key.startswith("FILE_SEARCH_STORE_") and value.startswith("fileSearchStores/"):
            store_ids.append(value)

    if not store_ids:
        raise ValueError("Keine FILE_SEARCH_STORE_* Einträge in .env gefunden.")

    return client, store_ids


CLIENT, STORE_IDS = load_client_and_stores()


def to_gemini_history(history, fallback_message):
    normalized = []

    for item in history or []:
        role = item.get("role")
        content = item.get("content") or item.get("text") or ""
        text = str(content).strip()

        if not text:
            continue

        gemini_role = "model" if role in {"assistant", "model"} else "user"
        normalized.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part(text=text)],
            )
        )

    if not normalized and fallback_message:
        normalized.append(
            types.Content(
                role="user",
                parts=[types.Part(text=fallback_message)],
            )
        )

    return normalized


def generate_answer(message, history):
    contents = to_gemini_history(history, message)

    response = CLIENT.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=STORE_IDS
                    )
                )
            ],
        ),
    )

    answer = response.text or "(Keine Antwort erhalten)"
    return answer, response


def extract_sources(response):
    sources = []

    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks
        for chunk in chunks or []:
            title = getattr(chunk.retrieved_context, "title", None)
            if title and title not in sources:
                sources.append(title)
    except Exception:
        return []

    return sources


class ChatHandler(BaseHTTPRequestHandler):

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        if self.path == "/api/debug-stores":
            try:
                response = CLIENT.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Content(
                        role="user",
                        parts=[types.Part(text="Was ist HaqqAI? Nenne alle Informationen die du über HaqqAI findest.")]
                    )],
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=STORE_IDS
                            )
                        )],
                    ),
                )
                chunks = []
                try:
                    raw = response.candidates[0].grounding_metadata.grounding_chunks
                    chunks = [getattr(c.retrieved_context, "title", "?") for c in (raw or [])]
                except Exception:
                    chunks = []

                self._send_json(200, {
                    "stores": STORE_IDS,
                    "answer": response.text,
                    "chunks_found": chunks,
                })
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Endpoint nicht gefunden."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Ungültiger JSON-Body."})
            return

        message = str(payload.get("message", "")).strip()
        history = payload.get("history") or []
        session_id = payload.get("session_id")

        if not message and not history:
            self._send_json(400, {"error": "'message' oder 'history' wird benötigt."})
            return

        try:
            answer, response = generate_answer(message, history)
            self._send_json(
                200,
                {
                    "answer": answer,
                    "session_id": session_id,
                    "sources": extract_sources(response),
                },
            )
        except Exception as exc:
            self._send_json(500, {"error": f"Backend-Fehler: {exc}"})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Chat-Backend läuft auf http://{HOST}:{PORT}")
    print(f"Geladene Stores ({len(STORE_IDS)}): {STORE_IDS}")

    server.serve_forever()