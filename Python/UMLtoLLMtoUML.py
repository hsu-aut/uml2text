import time
import threading
import pandas as pd
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
from flask import Flask, redirect, url_for, render_template_string
from openai import OpenAI
import openai
import os

# ─── Konfiguration ──────────────────────────────────────────────
EXCEL_FILE = "Liste_XMI.xlsx"       # Excel-Datei, aus der die Liste eingelesen wird
XMI_FOLDER = "XMI"                  # Ordner, in dem sich die XMI-Dateien befinden
OUTPUT_EXCEL = "Ergebnisse.xlsx"    # Excel-Datei, in die die Ergebnisse des Vorwärtsprozesses geschrieben werden
XMI_2_FOLDER = "XMI_2"              # Ordner für die XMI-Ausgabe des Rückwärtsprozesses

# OpenAI-Konfiguration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Globales Log-Array, in dem alle Nachrichten gesammelt werden
logs = []

def append_log(message):
    """Fügt eine Nachricht dem globalen Log hinzu und druckt sie in die Konsole."""
    global logs
    logs.append(message)
    print(message)

def extract_text_from_xmi(file_path):
    """
    Öffnet die XMI-Datei und liest den gesamten Textinhalt.
    Anstatt die XML-Struktur zu parsen, wird der ganze Dateiinhalt als String verwendet.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        append_log(f"Fehler beim Lesen von {file_path}: {e}")
        return None

def get_gpt_response(user_message, system_message=None):
    """
    Sendet eine Nachricht an das LLM (OpenAI ChatCompletion API) und gibt die Antwort zurück.
    Falls keine system_message angegeben wird, verwendet die Funktion den Standardprompt zur Analyse,
    ob es sich um ein Struktur- oder Ablaufdiagramm handelt.
    """
    if system_message is None:
        system_message = ("Analysiere die gegebenen UML-Daten und bestimme, ob es sich um ein "
                          "Struktur- oder Ablaufdiagramm handelt. Antworte ausschließlich mit 'Struktur' oder 'Ablauf'.")
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",  # Modell ggf. anpassen
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        append_log(error_msg)
        return error_msg

def get_gpt_response_2(user_message, system_message):
    """
    Sendet eine Nachricht an das LLM (OpenAI ChatCompletion API) und gibt die Antwort zurück.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",  # Modell ggf. anpassen
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        append_log(error_msg)
        return error_msg

def append_to_excel(file_name, diagram_type, llm_response, Gen_Antwort):
    """
    Fügt eine neue Zeile in die Excel-Ausgabedatei ein, bestehend aus:
    - Dateiname
    - Diagrammtyp (Ergebnis des ersten Prompts)
    - LLM Antwort (ursprünglicher generierter Text)
    - Gen Antwort (Antwort des zweiten Prompts)
    
    Die Antwort des Prompts wird damit in die vierte Spalte 'Gen Antwort' eingetragen.
    """
    new_data = pd.DataFrame([[file_name, diagram_type, llm_response, Gen_Antwort]], 
                            columns=["Dateiname", "Diagrammtyp", "LLM Antwort", "Gen Antwort"])
    if not os.path.exists(OUTPUT_EXCEL):
        new_data.to_excel(OUTPUT_EXCEL, index=False)
    else:
        # Lade die bestehenden Daten
        df_existing = pd.read_excel(OUTPUT_EXCEL)
        # Falls die existierenden Daten weniger als 4 Spalten haben, erweitern wir sie
        if df_existing.shape[1] < 4:
            df_existing["Gen Antwort"] = ""
        # Füge die neue Zeile hinzu und speichere die komplette Datei neu
        df_new = pd.concat([df_existing, new_data], ignore_index=True)
        df_new.to_excel(OUTPUT_EXCEL, index=False)
    append_log(f"✅ Eintrag für {file_name} gespeichert.")

# ─── Vorwärtsprozess (Encoder) ─────────────────────────────────────
def process_forward():
    """
    Liest zeilenweise die Excel-Datei 'Liste_XMI.xlsx' (bis Zeile 2827) ein und
    überprüft, ob in der 2. Spalte "English" und in der 3. Spalte "Yes" steht.
    Bei erfüllter Bedingung wird der Dateiname aus der 1. Spalte verwendet,
    um die entsprechende XMI-Datei aus dem Ordner 'XMI' einzulesen.
    Anschließend wird der Inhalt zuerst an das LLM gepromptet, ob es sich um ein
    Struktur- oder Ablaufdiagramm handelt. Nach Erhalt dieser Antwort wird der
    Inhalt der entsprechenden .txt Datei (Classes.txt bzw. Process.txt) vorangestellt,
    der XMI-Inhalt angehängt und dieser kombinierte Text an das LLM gesendet.
    Beide Antworten werden anschließend zusammen mit dem Dateinamen in eine Excel-Datei geschrieben.
    """
    append_log("Starte Vorwärtsprozess...")
    try:
        df = pd.read_excel(EXCEL_FILE)
        for idx, row in df.iterrows():
            if idx >= 2827:
                break
            # Annahme: Spalte 0 = Dateiname, Spalte 1 = Sprache, Spalte 2 = Flag (Yes/No)
            if str(row[1]).strip() == "English" and str(row[2]).strip() == "Yes":
                file_name = str(row[0]).strip()
                append_log(f"Verarbeite Datei: {file_name}")
                xmi_path = os.path.join(XMI_FOLDER, file_name)
                if not os.path.exists(xmi_path):
                    append_log(f"Datei {xmi_path} nicht gefunden.")
                    continue
                text = extract_text_from_xmi(xmi_path)
                if not text:
                    continue
                # Erster Prompt: Bestimmung, ob es sich um ein Struktur- oder Ablaufdiagramm handelt
                prompt_text = text + "\n\nob es sich um ein Struktur oder Ablauf Diagramm handelt"
                response1 = get_gpt_response(prompt_text)
                append_log(f"Erste LLM-Antwort für {file_name}: {response1}")
                # Abhängig von der Antwort, lese die entsprechende .txt Datei und setze sie vor den XMI-Inhalt
                prefix_text = ""
                if response1 == "Struktur":
                    try:
                        with open("Classes.txt", "r", encoding="utf-8") as f:
                            prefix_text = f.read()
                    except Exception as e:
                        append_log(f"Fehler beim Lesen von Classes.txt: {e}")
                elif response1 == "Ablauf":
                    try:
                        with open("Process.txt", "r", encoding="utf-8") as f:
                            prefix_text = f.read()
                    except Exception as e:
                        append_log(f"Fehler beim Lesen von Process.txt: {e}")
                else:
                    append_log(f"Unerwartete Antwort für {file_name}: {response1}. Überspringe Präfix.")
                # Füge den Inhalt der Datei vor den XMI-Text zusammen
                modified_text = prefix_text + "\n" + text
                # Zweiter Prompt: Mit Systemprompt, um eine finale Antwort zu generieren
                response2 = get_gpt_response_2(user_message=text, system_message=prefix_text)
                append_log(f"Zweite LLM-Antwort für {file_name}: {response2}")
                # Hier wird ein neuer Eintrag erstellt – in diesem Fall ist die vierte Spalte bereits belegt.
                append_to_excel(file_name, response1, response2, "")
                time.sleep(1)  # Kurze Pause, um Ratenlimits zu berücksichtigen
        append_log("Vorwärtsprozess abgeschlossen.")
    except Exception as e:
        append_log(f"Fehler im Vorwärtsprozess: {e}")

# ─── Rückwärtsprozess (Decoder) ────────────────────────────────────
def process_reverse():
    """
    Liest zeilenweise die Ergebnis-Excel-Datei ein, in der
    - Spalte 1: Dateiname,
    - Spalte 2: generierter Diagrammtyp und
    - Spalte 3: generierter Text (LLM Antwort)
    
    steht. Dieser generierte Text wird an das LLM gepromptet (z.B. "Erzeuge XMI basierend auf folgendem Text: ...").
    Die Antwort wird in eine XMI-Datei geschrieben und im Ordner 'XMI_2' abgelegt.
    Anschließend wird in der Excel-Datei in der vierten Spalte der jeweilige Prompt-Response eingetragen.
    """
    append_log("Starte Rückwärtsprozess...")
    try:
        if not os.path.exists(OUTPUT_EXCEL):
            append_log("Ausgabedatei Excel nicht gefunden.")
            return
        df = pd.read_excel(OUTPUT_EXCEL)
        for idx, row in df.iterrows():
            file_name = str(row["Dateiname"]).strip()
            generated_text = str(row["LLM Antwort"]).strip()
            dia_typ = str(row["Diagrammtyp"]).strip()
            append_log(f"Verarbeite Rückwärts für Datei: {file_name}")
            with open("Prompt_back.txt", "r", encoding="utf-8") as f:
                prompt_text = f.read()
            # Hole die Antwort des LLM (z.B. via API-Aufruf)
            response = get_gpt_response(user_message=generated_text, system_message=prompt_text)
            append_log(f"LLM-Antwort für {file_name} (Rückwärts): {response}")
            os.makedirs(XMI_2_FOLDER, exist_ok=True)
            output_file = os.path.join(XMI_2_FOLDER, "gen_" + os.path.splitext(file_name)[0] + ".xmi")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response)
            # Aktualisiere die vierte Spalte ("Gen Antwort") in der aktuellen Zeile
            df.loc[idx, "Gen Antwort"] = response
            time.sleep(1)
        df.to_excel(OUTPUT_EXCEL, index=False)
        append_log("Rückwärtsprozess abgeschlossen.")
    except Exception as e:
        append_log(f"Fehler im Rückwärtsprozess: {e}")

# ─── Web Interface (Flask HUD) ─────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def index():
    html = """
    <!doctype html>
    <html>
    <head>
        <title>LLM Anwendung</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            button { padding: 10px 20px; margin-right: 10px; }
            pre { background: #f4f4f4; padding: 10px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <h1>LLM Anwendung</h1>
        <a href="{{ url_for('start_forward') }}"><button>Vorwärtsprozess starten</button></a>
        <a href="{{ url_for('start_reverse') }}"><button>Rückwärtsprozess starten</button></a>
        <h2>Log:</h2>
        <pre>{{ logs }}</pre>
    </body>
    </html>
    """
    log_text = "\n".join(logs)
    return render_template_string(html, logs=log_text)  

@app.route("/start_forward")
def start_forward():
    threading.Thread(target=process_forward).start()
    return redirect(url_for("index"))

@app.route("/start_reverse")
def start_reverse():
    threading.Thread(target=process_reverse).start()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
