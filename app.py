import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE)
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
# 2. CONFIGURAZIONE E SESSION STATE
# ==================== =====================================
st.set_page_config(page_title="SOREU Alpina - Pro System", layout="wide", initial_sidebar_state="expanded")

# Inizializzazione variabili di sessione (Tutte quelle necessarie per la persistenza della simulazione)
if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None
if 'mezzo_selezionato' not in st.session_state: st.session_state.mezzo_selezionato = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False
if 'suono_riprodotto' not in st.session_state: st.session_state.suono_riprodotto = False
if 'log_chiamate' not in st.session_state: st.session_state.log_chiamate = []
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}

# Inizializzazione Database Mezzi
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "MSA 1 003": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5203, "lon": 9.7547, "tipo": "MSA", "sede": "Osp. Romano"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CRI_BG_162.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CBBG_014.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6725, "lon": 9.6450, "tipo": "MSB", "sede": "Croce Bianca Bergamo"},
        "CABG_301.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.7100, "lon": 9.6500, "tipo": "MSB", "sede": "Croce Azzurra Almenno"},
        "CRITRE_124.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5268, "lon": 9.5925, "tipo": "MSB", "sede": "CRI Treviglio"},
        "CRIDAL_118.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6475, "lon": 9.6012, "tipo": "MSB", "sede": "CRI Dalmine"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

# Inizializzazione Inventario/Consumabili
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {
        m: {"Ossigeno": 100, "Elettrodi": 25, "Bende": 15, "DPI": 40} for m in st.session_state.database_mezzi.keys()
    }

# Database Ospedali
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# =========================================================
# 3. LOGICA LOGIN (SBARRAMENTO)
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login Sistema")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}. Cambia la password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Password non valida.")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI", type="primary"):
            u_data = get_utente_db(u_in)
            if u_data and u_data[1] == p_in:
                if u_data[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("Accesso negato.")
    st.stop()

# =========================================================
# 4. FUNZIONI TECNICHE (ECG, DISTANZE, SUONI)
# =========================================================
def genera_tracciato_ecg(tipo="sinusale"):
    x = np.linspace(0, 10, 500)
    if tipo == "sinusale":
        y = np.sin(2 * np.pi * 1.2 * x) + 0.5 * np.sin(2 * np.pi * 2.4 * x) # Simula P-QRS-T
    elif tipo == "tachicardia":
        y = np.sin(2 * np.pi * 2.8 * x) + np.random.normal(0, 0.1, 500)
    else: # Piatto/Asistolia
        y = np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Time": x, "Voltage": y})

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
    vel = 220.0 if is_eli else 45.0
    return round(dist, 1), max(1, round((dist/vel)*60))

# =========================================================
# 5. CORE SIMULAZIONE (EVENTI E AUTOMAZIONI)
# =========================================================
# Database scenari
database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Bergamo", "via": "Piazza Vecchia", "lat": 45.7042, "lon": 9.6622},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]
scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore retrosternale forte.", "codice": "ROSSO", "tipo": "IMA", "msa": True},
    {"sintomi": "Trauma arto inferiore, sospetta frattura.", "codice": "GIALLO", "tipo": "TRAUMA", "msa": False},
    {"sintomi": "Paziente incosciente, respiro assente.", "codice": "ROSSO", "tipo": "ACR", "msa": True},
]

# Generatore automatico chiamate
tempo_necessario = 120 / st.session_state.time_mult
if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > tempo_necessario):
    if not st.session_state.evento_corrente:
        addr = random.choice(database_indirizzi)
        clin = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {**addr, **clin}
        st.session_state.last_mission_time = time.time()
        st.session_state.suono_riprodotto = False

# =========================================================
# 6. INTERFACCIA UTENTE (CENTRALE / MEZZO)
# =========================================================

# SIDEBAR DI STATO
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/ambulance.png", width=80)
    st.title("SOREU Alpina")
    st.write(f"👤 Utente: **{st.session_state.utente_connesso}**")
    
    if st.session_state.scrivania_selezionata:
        st.info(f"📍 Postazione: {st.session_state.scrivania_selezionata}")
        if st.button("⬅️ Cambia Ruolo"):
            st.session_state.scrivania_selezionata = None
            st.rerun()
    
    st.divider()
    if st.button("🚪 LOGOUT", type="secondary"):
        st.session_state.utente_connesso = None
        st.rerun()

# 6A. SELEZIONE SCRIVANIA
if st.session_state.scrivania_selezionata is None:
    st.header("🖥️ Benvenuto in Sala Operativa")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Centrale Operativa")
        for i in range(1, 4):
            if st.button(f"💻 Accedi Scrivania {i}", use_container_width=True):
                st.session_state.scrivania_selezionata = i
                st.session_state.ruolo = "centrale"
                st.rerun()
    with col2:
        st.subheader("Terminali Esterni")
        if st.button("🚑 Tablet Bordo Mezzo", type="primary", use_container_width=True):
            st.session_state.scrivania_selezionata = "TABLET"
            st.session_state.ruolo = "mezzo"
            st.rerun()

# 6B. INTERFACCIA CENTRALE
elif st.session_state.ruolo == "centrale":
    if not st.session_state.turno_iniziato:
        st.warning("Sistema in Standby.")
        if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
            st.session_state.turno_iniziato = True
            st.rerun()
    else:
        tab1, tab2, tab3 = st.tabs(["📟 GESTIONE EVENTI", "🚑 STATO RISORSE", "🏥 MONITOR OSPEDALI"])
        
        with tab1:
            c_ev, c_map = st.columns([1.5, 2])
            with c_ev:
                st.subheader("Chiamate NUE 112")
                if st.session_state.evento_corrente:
                    if not st.session_state.suono_riprodotto:
                        riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                    ev = st.session_state.evento_corrente
                    st.error(f"⚠️ {ev['codice']} - {ev['sintomi']}")
                    st.write(f"📍 {ev['via']}, {ev['comune']}")
                    
                    # Calcolo mezzi vicini
                    mezzi_liberi = [m for m, d in st.session_state.database_mezzi.items() if d["stato"] == "Libero in Sede"]
                    if mezzi_liberi:
                        scelta = st.multiselect("Invia Mezzi:", mezzi_liberi)
                        if st.button("🚀 INVIA MISSIONE", type="primary"):
                            for m in scelta:
                                st.session_state.database_mezzi[m]["stato"] = "1 - Partenza da sede"
                                st.session_state.missioni[m] = {
                                    "target": f"{ev['via']}, {ev['comune']}", "lat": ev['lat'], "lon": ev['lon'],
                                    "codice": ev['codice'], "timestamp": time.time(), "clinica": ev['tipo']
                                }
                                aggiungi_log_radio(m, f"Ricevuto. Partiamo per {ev['comune']} in codice {ev['codice']}.")
                            st.session_state.evento_corrente = None
                            st.rerun()
                else:
                    st.info("Nessun evento attivo al momento.")
            
            with c_map:
                st.subheader("Mappa Operativa")
                punti = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
                st.map(pd.DataFrame(punti), zoom=9)
                
                st.subheader("Radio Log")
                st.text_area("Comunicazioni Recenti", "\n".join(st.session_state.registro_radio[:15]), height=200)

        with tab2:
            st.subheader("Monitoraggio Flotta")
            for m, d in st.session_state.database_mezzi.items():
                with st.expander(f"{d['colore']} {m} - {d['stato']}"):
                    col_info, col_ecg = st.columns([1, 2])
                    with col_info:
                        st.write(f"Sede: {d['sede']}")
                        inv = st.session_state.inventario_mezzi[m]
                        st.progress(inv["Ossigeno"]/100, text=f"O2: {inv['Ossigeno']}%")
                        st.write(f"Elettrodi: {inv['Elettrodi']} | DPI: {inv['DPI']}")
                    with col_ecg:
                        if m in st.session_state.ecg_repository:
                            st.line_chart(st.session_state.ecg_repository[m], y="Voltage", height=150)
                            st.caption("Ultimo Tele-ECG ricevuto")
                        else:
                            st.caption("Nessun tracciato trasmesso.")

        with tab3:
            st.subheader("Disponibilità Pronto Soccorso")
            for osp, info in st.session_state.database_ospedali.items():
                col_o, col_b = st.columns([3, 1])
                col_o.write(f"**{osp}** ({info['pazienti']}/{info['max']})")
                col_o.progress(info['pazienti']/info['max'])
                if col_b.button("Libera Posto", key=f"lib_{osp}"):
                    if info['pazienti'] > 0: st.session_state.database_ospedali[osp]['pazienti'] -= 1; st.rerun()

# 6C. INTERFACCIA MEZZO
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.subheader("Login Equipaggio")
        scelta_m = st.selectbox("Seleziona il Mezzo:", list(st.session_state.database_mezzi.keys()))
        if st.button("CONFERMA EQUIPAGGIO"):
            st.session_state.mezzo_selezionato = scelta_m
            st.rerun()
    else:
        m_id = st.session_state.mezzo_selezionato
        dati = st.session_state.database_mezzi[m_id]
        inv = st.session_state.inventario_mezzi[m_id]
        
        st.header(f"📟 Terminale: {m_id}")
        
        col_stati, col_inv = st.columns([2, 1])
        with col_inv:
            st.subheader("📦 Scorta Bordo")
            st.write(f"O2: {inv['Ossigeno']}%")
            st.write(f"Elettrodi: {inv['Elettrodi']}")
            if st.button("Rifornisci in Sede"):
                st.session_state.inventario_mezzi[m_id] = {"Ossigeno": 100, "Elettrodi": 25, "Bende": 15, "DPI": 40}
                st.rerun()
        
        with col_stati:
            st.subheader(f"Stato: {dati['stato']}")
            in_miss = m_id in st.session_state.missioni
            
            c1, c2 = st.columns(2)
            if c1.button("🚨 STATO 1", use_container_width=True, disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "1 - Partenza da sede"; st.rerun()
            if c2.button("📍 STATO 2", use_container_width=True, disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "2 - Arrivo Posto"; st.rerun()
            if c1.button("🏥 STATO 3", use_container_width=True, disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "3 - Partenza Ospedale"; st.rerun()
            if c2.button("🏁 STATO 4", use_container_width=True, disabled=not in_miss, type="primary"):
                st.session_state.database_mezzi[m_id]["stato"] = "Libero in Sede"
                st.session_state.database_mezzi[m_id]["colore"] = "🟢"
                # Consumo ossigeno casuale
                st.session_state.inventario_mezzi[m_id]["Ossigeno"] -= random.randint(5, 15)
                del st.session_state.missioni[m_id]
                if m_id in st.session_state.ecg_repository: del st.session_state.ecg_repository[m_id]
                st.rerun()

        if in_miss:
            st.divider()
            st.subheader("📋 Scheda Clinica & ECG")
            miss = st.session_state.missioni[m_id]
            st.info(f"Target: {miss['target']} | Evento: {miss['clinica']}")
            
            col_param, col_grafico = st.columns([1, 2])
            with col_param:
                pa = st.slider("PA Sistolica", 40, 220, 120)
                fc = st.slider("FC Cardiaca", 30, 180, 80)
                if st.button("📉 ESEGUI ECG", type="primary", use_container_width=True):
                    if inv['Elettrodi'] >= 4:
                        st.session_state.inventario_mezzi[m_id]['Elettrodi'] -= 4
                        tipo_ritmo = "sinusale" if fc < 100 else "tachicardia"
                        if fc < 40: tipo_ritmo = "asistolia"
                        st.session_state.ecg_repository[m_id] = genera_tracciato_ecg(tipo_ritmo)
                        aggiungi_log_radio(m_id, f"ECG eseguito. Trasmesso in centrale per tele-consulto. Parametri: PA {pa}, FC {fc}.")
                        st.rerun()
                    else: st.error("Elettrodi insufficienti!")
            
            with col_grafico:
                if m_id in st.session_state.ecg_repository:
                    st.line_chart(st.session_state.ecg_repository[m_id], y="Voltage")
                    st.success("Tracciato Live caricato nel Monitor di Centrale")
