import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# =========================================================
# 1. DATABASE PERSISTENTE (SQLITE) - INTEGRATO
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stato_mezzi 
                 (nome TEXT PRIMARY KEY, ossigeno INTEGER, ecg_attivo INTEGER)''')
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO utenti VALUES (?,?,?,?)", [
            ('admin', 'admin', 0, 'Admin'),
            ('simone.putelli', 'simone', 1, 'Operatore'),
            ('simone.marinoni', 'simone', 1, 'Operatore')
        ])
    mezzi_list = ["MSA 02 001", "MSA 2 004", "MSA 1 003", "CRI_BG_161.C", "CRI_BG_162.C", "HORUS I-LMBD"]
    for m in mezzi_list:
        c.execute("INSERT OR IGNORE INTO stato_mezzi VALUES (?, 100, 0)", (m,))
    conn.commit()
    conn.close()

def get_utente_db(username):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT * FROM utenti WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res

def db_mezzi_update(nome, campo, valore):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute(f"UPDATE stato_mezzi SET {campo}=? WHERE nome=?", (valore, nome))
    conn.commit()
    conn.close()

def db_mezzi_get(nome):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT ossigeno, ecg_attivo FROM stato_mezzi WHERE nome=?", (nome,))
    res = c.fetchone()
    conn.close()
    return res if res else (100, 0)

init_db()

# =========================================================
# 2. LOGIN E SESSIONE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

if st.session_state.utente_connesso is None:
    st.title(" 🔐 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                conn = sqlite3.connect('centrale.db')
                conn.execute("UPDATE utenti SET password=?, cambio_obbligatorio=0 WHERE username=?", (n_p, st.session_state.temp_user))
                conn.commit(); conn.close()
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            user = get_utente_db(u_in)
            if user and user[1] == p_in:
                if user[2] == 1:
                    st.session_state.fase_cambio_pw, st.session_state.temp_user = True, u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
    st.stop()

# =========================================================
# 3. IL TUO CODICE ORIGINALE (INTEGRALE)
# =========================================================
def riproduci_suono_allarme():
    st.components.v1.html('<audio autoplay style="display:none;"><source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg" type="audio/ogg"></audio>', height=0)

def genera_ecg():
    t = np.linspace(0, 2, 1000)
    ecg = np.random.normal(0, 0.02, 1000)
    for i in [0.5, 1.5]: ecg += 1.5 * np.exp(-((t-i)**2)/0.0001)
    fig, ax = plt.subplots(figsize=(8, 2))
    ax.plot(t, ecg, color='#00FF00'); ax.set_facecolor('black'); fig.patch.set_facecolor('black')
    plt.xticks([]); plt.yticks([])
    return fig

# --- Inizializzazione Logiche (TUE) ---
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso"}
    }

for key, val in {
    'missioni': {}, 'registro_radio': [], 'scrivania_selezionata': None, 
    'ruolo': None, 'mezzo_selezionato': None, 'turno_iniziato': False,
    'evento_corrente': None, 'auto_mode': False, 'time_mult': 1.0
}.items():
    if key not in st.session_state: st.session_state[key] = val

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] {mittente}: {messaggio}")

# --- LOGICA AUTOMATICA (TUA) ---
if st.session_state.auto_mode and st.session_state.missioni:
    now = time.time()
    for m, miss in list(st.session_state.missioni.items()):
        tempo = now - miss.get("timestamp_creazione", now)
        if tempo > 60 and st.session_state.database_mezzi[m]["stato"] == "1 - Partenza da sede":
            st.session_state.database_mezzi[m]["stato"] = "2 - Arrivato su posto"
            aggiungi_log_radio(m, "STATO 2: Arrivati sul posto.")

# --- INTERFACCIA ---
if st.session_state.scrivania_selezionata is None:
    st.subheader("Selezione Postazione")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE"): st.session_state.scrivania_selezionata="CENTRALE"; st.session_state.ruolo="centrale"; st.rerun()
    if c2.button("🚑 MEZZO"): st.session_state.scrivania_selezionata="MEZZO"; st.session_state.ruolo="mezzo"; st.rerun()
else:
    if st.session_state.ruolo == "centrale":
        st.title(f"Sede SOREU Alpina - Postazione {st.session_state.scrivania_selezionata}")
        st.sidebar.toggle("Auto Mode", key="auto_mode")
        
        tab_map, tab_status = st.tabs(["Mappa Operativa", "Monitoraggio Risorse"])
        with tab_map:
            if st.button("Simula Emergenza"):
                st.session_state.evento_corrente = {"via": "Piazza Vecchia", "lat": 45.7042, "lon": 9.6622, "sintomi": "Sospetto IMA"}
                riproduci_suono_allarme(); st.rerun()
            if st.session_state.evento_corrente:
                st.warning(f"Chiamata in corso: {st.session_state.evento_corrente['sintomi']}")
                m_sel = st.selectbox("Invia:", list(st.session_state.database_mezzi.keys()))
                if st.button("ASSEGNA"):
                    st.session_state.database_mezzi[m_sel]["stato"] = "1 - Partenza da sede"
                    st.session_state.missioni[m_sel] = {"timestamp_creazione": time.time()}
                    st.session_state.evento_corrente = None; st.rerun()
            st.map(pd.DataFrame([{"lat": v["lat"], "lon": v["lon"]} for v in st.session_state.database_mezzi.values()]))
            
        with tab_status:
            for m, d in st.session_state.database_mezzi.items():
                o2, ecg_ok = db_mezzi_get(m)
                st.write(f"**{m}**: {d['stato']} | O2: {o2}%")
                if ecg_ok: st.pyplot(genera_ecg())

    elif st.session_state.ruolo == "mezzo":
        if st.session_state.mezzo_selezionato is None:
            st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
            if st.button("Login"): st.rerun()
        else:
            mio = st.session_state.mezzo_selezionato
            o2, ecg_ok = db_mezzi_get(mio)
            st.header(f"Terminale {mio}")
            c_a, c_b = st.columns(2)
            with c_a:
                if st.button("2 - Arrivo Posto"): 
                    st.session_state.database_mezzi[mio]["stato"]="2 - Arrivato su posto"; st.rerun()
                if st.button("3 - Partenza Osp.", disabled=not (ecg_ok and o2 > 20)):
                    db_mezzi_update(mio, "ossigeno", o2-25)
                    st.session_state.database_mezzi[mio]["stato"]="3 - Trasporto"; st.rerun()
                if st.button("4 - Libero"):
                    db_mezzi_update(mio, "ecg_attivo", 0)
                    st.session_state.database_mezzi[mio]["stato"]="Libero in Sede"; st.rerun()
            with c_b:
                if st.button("Trasmetti ECG"): db_mezzi_update(mio, "ecg_attivo", 1); st.rerun()
                if ecg_ok: st.pyplot(genera_ecg())
                st.write(f"O2 attuale: {o2}%")
                if st.button("Rifornimento"): db_mezzi_update(mio, "ossigeno", 100); st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.scrivania_selezionata = None; st.rerun()
