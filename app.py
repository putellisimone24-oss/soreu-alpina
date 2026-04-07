import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. DATABASE & LOGIN SYSTEM
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [
            ('admin', 'admin', 0, 'Admin'),
            ('simone.putelli', 'simone', 1, 'Operatore'),
            ('simone.marinoni', 'simone', 1, 'Operatore')
        ]
        c.executemany("INSERT INTO utenti VALUES (?,?,?,?)", utenti_iniziali)
    conn.commit()
    conn.close()

def get_utente_db(username):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT username, password, cambio_obbligatorio, ruolo FROM utenti WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res

def aggiorna_password_db(username, nuova_pw):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("UPDATE utenti SET password=?, cambio_obbligatorio=0 WHERE username=?", (nuova_pw, username))
    conn.commit()
    conn.close()

init_db()

# =========================================================
# 2. FUNZIONI TECNICHE (AUDIO, ECG, DISTANZE)
# =========================================================
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def genera_tracciato_ecg():
    x = np.linspace(0, 10, 500)
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo)

# =========================================================
# 3. CONFIGURAZIONE E SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}

# Inizializzazione variabili originali
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

for var in ['missioni', 'notifiche_centrale', 'registro_radio', 'scrivania_selezionata', 'ruolo', 'mezzo_selezionato', 'evento_corrente', 'last_mission_time', 'turno_iniziato', 'auto_mode', 'log_chiamate', 'time_mult']:
    if var not in st.session_state:
        st.session_state[var] = 1.0 if var == 'time_mult' else ([] if 'notifiche' in var or 'registro' in var or 'log' in var else ({} if var == 'missioni' else None))

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] 📻 {mittente}: {messaggio}")

# =========================================================
# 4. SCHERMATA LOGIN
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Errore password.")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            user = get_utente_db(u_in)
            if user and user[1] == p_in:
                if user[2] == 1:
                    st.session_state.fase_cambio_pw = True; st.session_state.temp_user = u_in; st.rerun()
                else:
                    st.session_state.utente_connesso = u_in; st.rerun()
            else: st.error("Credenziali errate.")
    st.stop()

# =========================================================
# 5. LOGICA TIMER AUTOMATICI (ORIGINALE)
# =========================================================
def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        mult = st.session_state.time_mult
        tempo = now - creazione
        if tempo < (30/mult):
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, "STATO 1: In movimento.")
        elif tempo < (60/mult):
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Sul target.")
        elif tempo >= (240/mult):
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, "STATO 4: Mezzo LIBERO.")
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

# =========================================================
# 6. INTERFACCIA PRINCIPALE
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.header(f"Benvenuto Operatore: {st.session_state.utente_connesso}")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA", use_container_width=True):
        st.session_state.scrivania_selezionata = "SALA"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 TABLET DI BORDO", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif st.session_state.ruolo == "centrale":
    st.sidebar.button("🔙 Menu", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
    st.sidebar.toggle("🤖 Automatizza Equipaggi", key="auto_mode")
    tab1, tab2, tab3 = st.tabs(["📟 Missioni", "🗺️ Mappa", "📊 Tele-ECG"])
    
    with tab1:
        st.subheader("Gestione Chiamate")
        if st.button("🚨 GENERA TARGET"):
            st.session_state.evento_corrente = {"via": f"Via Roma {random.randint(1,90)}", "codice": "ROSSO"}
            riproduci_suono_allarme()
        if st.session_state.evento_corrente:
            ev = st.session_state.evento_corrente
            st.warning(f"Target: {ev['via']}")
            mezzo = st.selectbox("Invia:", list(st.session_state.database_mezzi.keys()))
            if st.button("🚀 INVIA"):
                st.session_state.missioni[mezzo] = {"target": ev['via'], "timestamp_creazione": time.time()}
                st.session_state.evento_corrente = None; st.rerun()
        st.write("Missioni attive:", st.session_state.missioni)

    with tab2:
        st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))

    with tab3:
        st.subheader("ECG Ricevuti")
        for m, ecg in st.session_state.ecg_repository.items():
            with st.expander(f"🚑 Tracciato {m}"):
                st.line_chart(ecg, x="Tempo", y="mV")

elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("ACCEDI"): st.rerun()
    else:
        m_id = st.session_state.mezzo_selezionato
        inv = st.session_state.inventario_mezzi[m_id]
        st.title(f"🚑 Tablet: {m_id}")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("📦 Inventario")
            st.metric("O2", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("🔄 Rifornimento"):
                st.session_state.inventario_mezzi[m_id] = {"O2": 100, "Elettrodi": 20}; st.rerun()
        with c2:
            st.subheader("🩺 Monitor")
            if st.button("📉 TRASMETTI ECG", type="primary"):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[m_id]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[m_id] = genera_tracciato_ecg()
                    st.rerun()
                else: st.error("Elettrodi esauriti!")
            if m_id in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[m_id], x="Tempo", y="mV")
            if st.button("🏁 CHIUDI INTERVENTO"):
                st.session_state.inventario_mezzi[m_id]["O2"] -= 10
                if m_id in st.session_state.ecg_repository: del st.session_state.ecg_repository[m_id]
                if m_id in st.session_state.missioni: del st.session_state.missioni[m_id]
                st.session_state.database_mezzi[m_id]["stato"] = "Libero in Sede"
                st.rerun()
