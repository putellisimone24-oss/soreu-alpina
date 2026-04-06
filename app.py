import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. DATABASE SQLITE E LOGICA DIAGNOSTICA
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [('admin', 'admin', 0, 'Admin'),
                           ('simone.putelli', 'simone', 1, 'Operatore'),
                           ('simone.marinoni', 'simone', 1, 'Operatore')]
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

def genera_tracciato_ecg():
    x = np.linspace(0, 10, 500)
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

init_db()

# =========================================================
# 2. CONFIGURAZIONE E SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}

# Inizializzazione Database Mezzi
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI"}
    }

if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

for key in ['missioni', 'registro_radio', 'notifiche_centrale', 'scrivania_selezionata', 'ruolo', 'turno_iniziato']:
    if key not in st.session_state: st.session_state[key] = [] if 'registro' in key or 'notifiche' in key else ({} if key == 'missioni' else None)

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] 📻 {mittente}: {messaggio}")

# =========================================================
# 3. INTERFACCIA LOGIN
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 Login SOREU Alpina")
    if st.session_state.fase_cambio_pw:
        n_p = st.text_input("Nuova Password", type="password")
        if st.button("SALVA"):
            aggiorna_password_db(st.session_state.temp_user, n_p)
            st.session_state.utente_connesso = st.session_state.temp_user
            st.rerun()
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            res = get_utente_db(u_in)
            if res and res[1] == p_in:
                if res[2] == 1:
                    st.session_state.fase_cambio_pw = True; st.session_state.temp_user = u_in; st.rerun()
                else:
                    st.session_state.utente_connesso = u_in; st.rerun()
            else: st.error("Credenziali errate")
    st.stop()

# =========================================================
# 4. DASHBOARD PRINCIPALE
# =========================================================
if st.session_state.scrivania_selezionata is None:
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE SOREU", use_container_width=True):
        st.session_state.scrivania_selezionata = "SALA"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 TABLET MEZZO", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif st.session_state.ruolo == "centrale":
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
    t1, t2, t3 = st.tabs(["📟 Missioni", "🗺️ Mappa", "📊 ECG Tele-Consulto"])
    
    with t1: st.write("Gestione missioni attiva...")
    with t2: st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))
    with t3:
        for m, ecg in st.session_state.ecg_repository.items():
            st.write(f"🚑 ECG ricevuto da: {m}")
            st.line_chart(ecg, x="Tempo", y="mV")

elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("CONNETTI"): st.rerun()
    else:
        m = st.session_state.mezzo_selezionato
        inv = st.session_state.inventario_mezzi[m]
        st.title(f"📟 Terminale {m}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Ossigeno", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            pa = st.slider("PA Sistolica", 50, 200, 120)
            fc = st.slider("Freq. Cardiaca", 30, 180, 80)
            
        with col2:
            if st.button("📉 TRASMETTI ECG", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[m]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[m] = genera_tracciato_ecg()
                    aggiungi_log_radio(m, "ECG inviato in centrale per tele-consulto.")
                    st.rerun()
                else: st.error("Elettrodi esauriti!")

            if m in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[m], x="Tempo", y="mV")

            if st.button("🏁 CHIUDI INTERVENTO"):
                st.session_state.inventario_mezzi[m]["O2"] -= 10
                if m in st.session_state.ecg_repository: del st.session_state.ecg_repository[m]
                st.session_state.database_mezzi[m]["stato"] = "Libero in Sede"
                st.rerun()
