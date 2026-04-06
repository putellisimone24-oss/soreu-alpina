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
# 2. CONFIGURAZIONE E INIZIALIZZAZIONE SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide", initial_sidebar_state="expanded")

# Inizializzazione variabili di sessione
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

# 1. DATABASE MEZZI SANITARI REALI (Dal tuo codice)
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

# 2. SISTEMA CONSUMABILI (Nuova aggiunta)
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {
        m: {"O2": 100, "Elettrodi": 20, "DPI": 50} for m in st.session_state.database_mezzi.keys()
    }

# 3. DATABASE OSPEDALI REALI (Dal tuo codice)
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# =========================================================
# 3. SCHERMATA LOGIN (SBARRAMENTO)
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login Sistema")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}: Imposta una nuova password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Le password non coincidono o sono troppo brevi.")
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
# 4. FUNZIONI TECNICHE (AUDIO, ECG, LOGICA)
# =========================================================
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def genera_tracciato_ecg(ritmo="sinusale"):
    x = np.linspace(0, 10, 500)
    if ritmo == "sinusale":
        y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    elif ritmo == "tachicardia":
        y = np.sin(x * 2.8 * 2 * np.pi) + np.random.normal(0, 0.1, 500)
    else: # Asistolia
        y = np.random.normal(0, 0.02, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo_minuti)

# =========================================================
# 5. LOGICA AUTOMATIZZAZIONE (Dal tuo codice)
# =========================================================
def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        tempo_trascorso = (now - miss["timestamp_creazione"]) * st.session_state.time_mult
        db = st.session_state.database_mezzi
        if tempo_trascorso < 30:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, "STATO 1: In movimento verso l'evento.")
        elif tempo_trascorso < 90:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Sul posto, inizio valutazione.")
        elif tempo_trascorso < 180:
            if db[m_nome]["stato"] != "3 - Partenza per ospedale":
                db[m_nome]["stato"] = "3 - Partenza per ospedale"
                aggiungi_log_radio(m_nome, f"STATO 3: Caricato, direzione {miss['ospedale_assegnato']}.")
        elif tempo_trascorso >= 240:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, "STATO 4: Libero e operativo.")
            st.session_state.inventario_mezzi[m_nome]["O2"] -= random.randint(5, 15)
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

# =========================================================
# 6. GENERAZIONE EVENTI (Dal tuo codice)
# =========================================================
database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]
scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore retrosternale.", "codice": "ROSSO", "patologia": "Sospetto IMA"},
    {"sintomi": "Trauma motociclista, cosciente.", "codice": "GIALLO", "patologia": "Trauma"},
    {"sintomi": "Paziente incosciente, gasping.", "codice": "ROSSO", "patologia": "Arresto Cardiaco"}
]

if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > (120/st.session_state.time_mult)):
    if not st.session_state.evento_corrente:
        addr = random.choice(database_indirizzi); clin = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {**addr, **clin}
        st.session_state.last_mission_time = time.time()
        st.session_state.suono_riprodotto = False

# =========================================================
# 7. INTERFACCIA UTENTE (SALA OPERATIVA / MEZZO)
# =========================================================

# --- BARRA LATERALE ---
with st.sidebar:
    st.title("🚑 SOREU Alpina")
    st.write(f"Utente: **{st.session_state.utente_connesso}**")
    if st.session_state.scrivania_selezionata:
        if st.button("⬅️ CAMBIA RUOLO"):
            st.session_state.scrivania_selezionata = None; st.rerun()
    st.divider()
    if st.button("🚪 LOGOUT"):
        st.session_state.utente_connesso = None; st.rerun()

# SELEZIONE POSTAZIONE
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🖥️ Scrivania Centrale", use_container_width=True):
            st.session_state.scrivania_selezionata = "CENTRALE"; st.session_state.ruolo = "centrale"; st.rerun()
    with col2:
        if st.button("🚑 Tablet Mezzo", use_container_width=True):
            st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# --- LOGICA CENTRALE ---
elif st.session_state.ruolo == "centrale":
    if not st.session_state.turno_iniziato:
        st.info("Sistema pronto. Inizia il turno per ricevere chiamate.")
        if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
            st.session_state.turno_iniziato = True; st.rerun()
    else:
        st.sidebar.subheader("Opzioni")
        st.session_state.auto_mode = st.sidebar.toggle("🤖 Automazione Equipaggi", value=st.session_state.auto_mode)
        st.session_state.time_mult = st.sidebar.select_slider("Velocità", options=[1.0, 2.0, 5.0, 10.0], value=st.session_state.time_mult)

        tab1, tab2, tab3 = st.tabs(["📟 Missioni", "🗺️ Mappa & Radio", "🚑 Risorse & ECG"])
        
        with tab1:
            if st.session_state.evento_corrente:
                if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                ev = st.session_state.evento_corrente
                st.error(f"🚨 CHIAMATA: {ev['sintomi']} a {ev['comune']}")
                mezzi_liberi = [m for m, d in st.session_state.database_mezzi.items() if d["stato"] == "Libero in Sede"]
                m_scelto = st.selectbox("Assegna Mezzo", mezzi_liberi)
                osp_scelto = st.selectbox("Ospedale pre-allertato", list(st.session_state.database_ospedali.keys()))
                if st.button("🚀 INVIA MISSIONE", use_container_width=True):
                    st.session_state.missioni[m_scelto] = {
                        "target": ev['via'], "ospedale_assegnato": osp_scelto, "timestamp_creazione": time.time(), "patologia": ev['patologia']
                    }
                    st.session_state.database_mezzi[m_scelto]["stato"] = "In Missione"; st.session_state.evento_corrente = None; st.rerun()
            else: st.info("In attesa di chiamate...")

        with tab2:
            c_map, c_rad = st.columns([2, 1])
            with c_map:
                punti = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
                st.map(pd.DataFrame(punti))
            with c_rad:
                st.subheader("Radio Log")
                st.text_area("Live Radio", "\n".join(st.session_state.registro_radio[:15]), height=300)

        with tab3:
            st.subheader("Monitoraggio Flotta")
            for m, d in st.session_state.database_mezzi.items():
                with st.expander(f"🚑 {m} - {d['stato']}"):
                    inv = st.session_state.inventario_mezzi[m]
                    st.write(f"O2: {inv['O2']}% | Elettrodi: {inv['Elettrodi']}")
                    if m in st.session_state.ecg_repository:
                        st.line_chart(st.session_state.ecg_repository[m], x="Tempo", y="mV")
                        st.caption("Ultimo ECG ricevuto dal campo")

# --- LOGICA MEZZO ---
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        m_sel = st.selectbox("Identificativo Mezzo:", list(st.session_state.database_mezzi.keys()))
        if st.button("ACCEDI"): st.session_state.mezzo_selezionato = m_sel; st.rerun()
    else:
        m_id = st.session_state.mezzo_selezionato
        inv = st.session_state.inventario_mezzi[m_id]
        st.header(f"📟 Terminale: {m_id}")
        
        col_m1, col_m2 = st.columns([1, 2])
        with col_m1:
            st.metric("Ossigeno", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("Rifornisci Sede"): 
                st.session_state.inventario_mezzi[m_id] = {"O2": 100, "Elettrodi": 20, "DPI": 50}; st.rerun()

        with col_m2:
            if m_id in st.session_state.missioni:
                miss = st.session_state.missioni[m_id]
                st.info(f"Target: {miss['target']} | Clinica: {miss['patologia']}")
                
                # PULSANTIERA OPERATIVA (Dalla tua richiesta)
                c_p1, c_p2 = st.columns(2)
                if c_p1.button("🚨 PARTENZA"): st.session_state.database_mezzi[m_id]["stato"] = "1 - Partenza da sede"; st.rerun()
                if c_p2.button("📍 ARRIVO POSTO"): st.session_state.database_mezzi[m_id]["stato"] = "2 - Arrivato su posto"; st.rerun()
                
                st.divider()
                st.subheader("🩺 Parametri & ECG")
                fc = st.slider("Frequenza Cardiaca", 30, 180, 80)
                
                # TASTO ESEGUI ECG (Aggiunta richiesta)
                if st.button("📉 ESEGUI ECG", type="primary", use_container_width=True):
                    if inv['Elettrodi'] >= 4:
                        st.session_state.inventario_mezzi[m_id]['Elettrodi'] -= 4
                        ritmo = "sinusale" if fc < 100 else "tachicardia"
                        st.session_state.ecg_repository[m_id] = genera_tracciato_ecg(ritmo)
                        aggiungi_log_radio(m_id, f"ECG eseguito (FC: {fc}). Trasmesso in Centrale.")
                        st.rerun()
                    else: st.error("Elettrodi esauriti!")
                
                if m_id in st.session_state.ecg_repository:
                    st.line_chart(st.session_state.ecg_repository[m_id], x="Tempo", y="mV")
                
                if st.button("🏁 CHIUDI MISSIONE"):
                    st.session_state.database_mezzi[m_id]["stato"] = "Libero in Sede"
                    st.session_state.inventario_mezzi[m_id]["O2"] -= 10
                    del st.session_state.missioni[m_id]
                    if m_id in st.session_state.ecg_repository: del st.session_state.ecg_repository[m_id]
                    st.rerun()
            else:
                st.success("In attesa di missione dalla Centrale...")
