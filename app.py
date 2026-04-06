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
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE)
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    # Tabella Utenti (Tua originale)
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    
    # Tabella Stato Mezzi (Nuova: per Consumabili e ECG)
    c.execute('''CREATE TABLE IF NOT EXISTS stato_mezzi 
                 (nome TEXT PRIMARY KEY, ossigeno INTEGER, presidi INTEGER, ecg_attivo INTEGER)''')
    
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [
            ('admin', 'admin', 0, 'Admin'),
            ('simone.putelli', 'simone', 1, 'Operatore'),
            ('simone.marinoni', 'simone', 1, 'Operatore')
        ]
        c.executemany("INSERT INTO utenti VALUES (?,?,?,?)", utenti_iniziali)
    
    # Inizializzazione Mezzi nel DB
    mezzi_nomi = ["MSA 02 001", "MSA 2 004", "MSA 1 003", "CRI_BG_161.C", "CRI_BG_162.C", 
                  "CBBG_014.C", "CABG_301.C", "CRITRE_124.C", "CRITRE_135.C", 
                  "CRIHBG_154.C", "CRIDAL_118.C", "HORUS I-LMBD"]
    for nome in mezzi_nomi:
        c.execute("INSERT OR IGNORE INTO stato_mezzi VALUES (?, 100, 10, 0)", (nome,))
        
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

# Funzioni di supporto per stato mezzi nel DB
def db_mezzi_update(nome, campo, valore):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute(f"UPDATE stato_mezzi SET {campo}=? WHERE nome=?", (valore, nome))
    conn.commit()
    conn.close()

def db_mezzi_get(nome):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT ossigeno, presidi, ecg_attivo FROM stato_mezzi WHERE nome=?", (nome,))
    res = c.fetchone()
    conn.close()
    return res

init_db()

# =========================================================
# 2. FUNZIONI CLINICHE (ECG)
# =========================================================
def genera_ecg_plot():
    fs = 500
    t = np.linspace(0, 2, fs * 2)
    ecg = np.zeros_like(t)
    for i in [0.4, 1.2]: 
        ecg += 0.2 * np.exp(-((t - (i - 0.15))**2) / 0.001) # P
        ecg += 1.5 * np.exp(-((t - i)**2) / 0.00005)        # QRS
        ecg += 0.4 * np.exp(-((t - (i + 0.25))**2) / 0.005) # T
    ecg += np.random.normal(0, 0.03, len(t))
    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.plot(t, ecg, color='#00FF00', linewidth=1.5)
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    ax.grid(color='#004400', linestyle='-', linewidth=0.5)
    plt.xticks([]); plt.yticks([])
    return fig

# =========================================================
# 3. SCHERMATA LOGIN
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

if st.session_state.utente_connesso is None:
    st.title(" SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        st.warning(f" Primo accesso per {st.session_state.temp_user}: Imposta una nuova password.")
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
        if st.button("ACCEDI", type="primary"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("ID o Password errati.")
    st.stop()

# =========================================================
# 4. IL TUO CODICE ORIGINALE INTEGRALE
# =========================================================
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>', height=0)

if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "MSA 1 003": {"stato": "Libero in Sede", "colore": "", "lat": 45.5203, "lon": 9.7547, "tipo": "MSA", "sede": "Osp. Romano"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CRI_BG_162.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CBBG_014.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.6725, "lon": 9.6450, "tipo": "MSB", "sede": "Croce Bianca Bergamo"},
        "CABG_301.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.7100, "lon": 9.6500, "tipo": "MSB", "sede": "Croce Azzurra Almenno"},
        "CRITRE_124.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.5268, "lon": 9.5925, "tipo": "MSB", "sede": "CRI Treviglio"},
        "CRITRE_135.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.5532, "lon": 9.6198, "tipo": "MSB", "sede": "CRI Treviglio"},
        "CRIHBG_154.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.5940, "lon": 9.6910, "tipo": "MSB", "sede": "CRI Urgnano"},
        "CRIDAL_118.C": {"stato": "Libero in Sede", "colore": "", "lat": 45.6475, "lon": 9.6012, "tipo": "MSB", "sede": "CRI Dalmine"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# Inizializzazione variabili sessione
for key, val in {
    'missioni': {}, 'notifiche_centrale': [], 'registro_radio': [], 
    'scrivania_selezionata': None, 'ruolo': None, 'mezzo_selezionato': None,
    'turno_iniziato': False, 'richiesta_chiusura': False, 'evento_corrente': None,
    'last_mission_time': time.time(), 'time_mult': 1.0, 'auto_mode': False,
    'suono_riprodotto': False, 'log_chiamate': []
}.items():
    if key not in st.session_state: st.session_state[key] = val

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    vel = 220.0 if is_eli else 45.0
    tm = round((dist/vel)*60) + (2 if is_eli else 0)
    return round(dist, 1), max(1, tm)

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] {mittente}: {messaggio}")

# --- LOGICA OPERATIVA ---
col_titolo, col_orologio = st.columns([3, 1])
with col_titolo: st.title(" SOREU Alpina - Sala Operativa")
with col_orologio: st.metric(" Orario Reale", datetime.now().strftime("%H:%M:%S"))

if st.session_state.scrivania_selezionata is None:
    st.subheader(" Selezione Postazione di Lavoro")
    c1, c2, c3 = st.columns(3)
    if c1.button("Scrivania 1", use_container_width=True): st.session_state.scrivania_selezionata=1; st.session_state.ruolo="centrale"; st.rerun()
    if c3.button("Mezzo (Esterno)", use_container_width=True): st.session_state.scrivania_selezionata="MEZZO"; st.session_state.ruolo="mezzo"; st.rerun()
elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    if st.button(" INIZIA TURNO ", type="primary", use_container_width=True): st.session_state.turno_iniziato=True; st.rerun()
else:
    # --- INTERFACCIA CENTRALE ---
    if st.session_state.ruolo == "centrale":
        tab_invio, tab_risorse, tab_ps = st.tabs([" Nuove Missioni", " Stato Risorse", " Monitoraggio PS"])
        
        with tab_invio:
            col_ev, col_mappa = st.columns([1.5, 2])
            with col_ev:
                if st.button("Forza Chiamata"):
                    st.session_state.evento_corrente = {"via": "Piazza Vecchia", "comune": "Bergamo", "lat": 45.7042, "lon": 9.6622, "sintomi": "Dolore toracico", "codice_reale": "ROSSO"}
                    riproduci_suono_allarme(); st.rerun()
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.warning(f"TARGET: {ev['via']}, {ev['comune']}")
                    mezzo = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
                    if st.button("INVIA MEZZO"):
                        st.session_state.missioni[mezzo] = {"target": ev['via'], "timestamp_creazione": time.time(), "ospedale_assegnato": "Osp. Papa Giovanni XXIII (BG)"}
                        st.session_state.database_mezzi[mezzo]["stato"] = "1 - Partenza da sede"
                        st.session_state.evento_corrente = None; st.rerun()
            with col_mappa:
                st.map(pd.DataFrame([{"lat": v["lat"], "lon": v["lon"]} for v in st.session_state.database_mezzi.values()]))

        with tab_risorse:
            for m, d in st.session_state.database_mezzi.items():
                params = db_mezzi_get(m)
                with st.expander(f"{m} - {d['stato']}"):
                    c1, c2 = st.columns([1, 2])
                    c1.write(f"O2: {params[0]}% | Kit: {params[1]}")
                    if params[2] == 1: 
                        with c2: st.pyplot(genera_ecg_plot())
                    else: c2.info("Nessuna telemetria ECG attiva.")

    # --- INTERFACCIA MEZZO ---
    elif st.session_state.ruolo == "mezzo":
        if st.session_state.mezzo_selezionato is None:
            st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
            if st.button("Login Mezzo"): st.rerun()
        else:
            mio = st.session_state.mezzo_selezionato
            params = db_mezzi_get(mio)
            st.header(f"Terminale {mio}")
            
            c_stati, c_scheda = st.columns([1, 1.5])
            with c_stati:
                if st.button("2 - Arrivo Posto"): 
                    st.session_state.database_mezzi[mio]["stato"]="2 - Arrivato su posto"; st.rerun()
                
                # Blocco Trasporto (Stato 3): Richiede ECG fatto e O2 > 15
                puo_trasportare = (params[2] == 1 and params[0] > 15)
                if st.button("3 - Partenza Ospedale", disabled=not puo_trasportare):
                    db_mezzi_update(mio, "ossigeno", params[0]-25)
                    st.session_state.database_mezzi[mio]["stato"]="3 - Partenza per ospedale"; st.rerun()
                
                if st.button("4 - Libero"):
                    db_mezzi_update(mio, "ecg_attivo", 0)
                    st.session_state.database_mezzi[mio]["stato"]="Libero in Sede"
                    if mio in st.session_state.missioni: del st.session_state.missioni[mio]
                    st.rerun()

            with c_scheda:
                st.subheader("Parametri Vitali")
                pa = st.slider("PA Sistolica", 50, 200, 120)
                fc = st.slider("FC", 30, 180, 80)
                if st.button("💓 ESEGUI E TRASMETTI ECG"):
                    db_mezzi_update(mio, "ecg_attivo", 1)
                    st.pyplot(genera_ecg_plot())
                    st.success("Tracciato inviato in Centrale!")
                
                st.divider()
                st.write(f"Scorte O2: {params[0]}% | Kit: {params[1]}")
                if st.button("Rifornimento Mezzo"):
                    db_mezzi_update(mio, "ossigeno", 100); db_mezzi_update(mio, "presidi", 10); st.rerun()
