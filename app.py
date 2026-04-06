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
    # Tabella Utenti (Tua esistente)
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    
    # Tabella Stato Mezzi (Nuova: per Consumabili e ECG persistente)
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
    
    # Inizializzazione Mezzi nel DB se non presenti
    mezzi_list = ["MSA 02 001", "MSA 2 004", "MSA 1 003", "CRI_BG_161.C", "CRI_BG_162.C", 
                  "CBBG_014.C", "CABG_301.C", "CRITRE_124.C", "CRITRE_135.C", 
                  "CRIHBG_154.C", "CRIDAL_118.C", "HORUS I-LMBD"]
    for m in mezzi_list:
        c.execute("INSERT OR IGNORE INTO stato_mezzi VALUES (?, 100, 10, 0)", (m,))
        
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
# 2. FUNZIONI CLINICHE E UTILITY
# =========================================================
def genera_grafico_ecg():
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

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>', height=0)

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    dist = math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2) * 111
    vel = 220.0 if is_eli else 45.0
    tempo = round((dist / vel) * 60)
    return round(dist, 1), max(1, tempo)

# =========================================================
# 3. LOGIN E SESSIONE
# =========================================================
st.set_page_config(page_title="SOREU Alpina PRO", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

if st.session_state.utente_connesso is None:
    st.title(" SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
    st.stop()

# =========================================================
# 4. DATABASE LOCALE SESSION_STATE (Dati Temporanei)
# =========================================================
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso"}
    }

if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] {mittente}: {messaggio}")

# =========================================================
# 5. INTERFACCIA OPERATIVA
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.subheader(" Selezione Postazione")
    col1, col2 = st.columns(2)
    if col1.button("🎧 CENTRALE OPERATIVA"):
        st.session_state.scrivania_selezionata = "CENTRALE"; st.session_state.ruolo = "centrale"; st.rerun()
    if col2.button("🚑 EQUIPAGGIO MEZZO"):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()
else:
    # --- SIDEBAR COMUNE ---
    st.sidebar.title(f"📍 {st.session_state.scrivania_selezionata}")
    if st.sidebar.button("Cambia Ruolo / Logout"):
        st.session_state.scrivania_selezionata = None
        st.rerun()

    # ==================== LOGICA CENTRALE ====================
    if st.session_state.ruolo == "centrale":
        tab_invio, tab_risorse = st.tabs([" Chiamate", " Monitoraggio Mezzi"])
        
        with tab_invio:
            col_ev, col_map = st.columns([1, 1.5])
            with col_ev:
                if st.button(" Forza Chiamata 112"):
                    st.session_state.evento_corrente = {"via": "Piazza Vecchia", "comune": "Bergamo", "lat": 45.7042, "lon": 9.6622, "sintomi": "Sospetto IMA, dolore toracico"}
                    riproduci_suono_allarme(); st.rerun()
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.warning(f"EVENTO: {ev['sintomi']} in {ev['via']}")
                    mezzo_scelto = st.selectbox("Invia Mezzo", list(st.session_state.database_mezzi.keys()))
                    if st.button("INVIA"):
                        st.session_state.missioni[mezzo_scelto] = {"target": ev['via'], "lat": ev['lat'], "lon": ev['lon']}
                        st.session_state.database_mezzi[mezzo_scelto]["stato"] = "1 - Partenza"
                        st.session_state.evento_corrente = None; st.rerun()
            with col_map:
                st.map(pd.DataFrame([{"lat": v["lat"], "lon": v["lon"]} for v in st.session_state.database_mezzi.values()]))

        with tab_risorse:
            for m, d in st.session_state.database_mezzi.items():
                params = db_mezzi_get(m)
                c1, c2 = st.columns([1, 2])
                c1.write(f"**{m}**\n{d['stato']}\nO2: {params[0]}%")
                if params[2] == 1:
                    with c2: st.pyplot(genera_grafico_ecg())
                else:
                    c2.info("Nessuna Telemetria")

    # ==================== LOGICA MEZZO ====================
    elif st.session_state.ruolo == "mezzo":
        mio_mezzo = st.selectbox("Seleziona il tuo Mezzo", list(st.session_state.database_mezzi.keys()))
        params = db_mezzi_get(mio_mezzo)
        
        st.title(f"📟 Terminale {mio_mezzo}")
        col_btn, col_clinica = st.columns([1, 1.5])
        
        with col_btn:
            st.subheader("Stati")
            if st.button("2 - Arrivo Posto"):
                st.session_state.database_mezzi[mio_mezzo]["stato"] = "2 - Arrivo Posto"; st.rerun()
            
            # Blocco: Se O2 < 15 o ECG non fatto, non vai in Stato 3
            puo_partire = (params[2] == 1 and params[0] > 15)
            if st.button("3 - Partenza Osp.", disabled=not puo_partire):
                db_mezzi_update(mio_mezzo, "ossigeno", params[0]-20)
                db_mezzi_update(mio_mezzo, "presidi", params[1]-1)
                st.session_state.database_mezzi[mio_mezzo]["stato"] = "3 - Trasporto"; st.rerun()
            
            if st.button("4 - Libero"):
                db_mezzi_update(mio_mezzo, "ecg_attivo", 0)
                st.session_state.database_mezzi[mio_mezzo]["stato"] = "Libero in Sede"
                if mio_mezzo in st.session_state.missioni: del st.session_state.missioni[mio_mezzo]
                st.rerun()
        
        with col_clinica:
            st.subheader("Scheda Paziente")
            if st.button("💓 ESEGUI ECG"):
                db_mezzi_update(mio_mezzo, "ecg_attivo", 1)
                st.pyplot(genera_grafico_ecg())
                st.success("ECG Trasmesso alla SOREU")
                st.rerun()
            
            st.write(f"Scorte Ossigeno: {params[0]}%")
            if params[0] < 20: st.error("⚠️ Rifornire Ossigeno!")
            if st.button("Rifornimento Totale"):
                db_mezzi_update(mio_mezzo, "ossigeno", 100)
                db_mezzi_update(mio_mezzo, "presidi", 10); st.rerun()
