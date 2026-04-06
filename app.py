import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE) - AGGIUNTO
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

def aggiungi_nuovo_utente_db(username, password, ruolo='Operatore'):
    try:
        conn = sqlite3.connect('centrale.db')
        c = conn.cursor()
        c.execute("INSERT INTO utenti VALUES (?,?,?,?)", (username, password, 1, ruolo))
        conn.commit()
        conn.close()
        return True
    except: return False

init_db()

# =========================================================
# 2. CONFIGURAZIONE PAGINA E SICUREZZA LOGIN
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# --- LOGICA DI LOGIN ---
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Accesso Sistema")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}. Imposta una nuova password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Le password non coincidono o sono troppo brevi (min 4 car).")
    else:
        u_in = st.text_input("ID Utente (es. simone.putelli)").lower().strip()
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
            else: st.error("Credenziali errate.")
    st.stop()

# =========================================================
# 3. IL TUO SISTEMA ORIGINALE (FUNZIONI E DATI)
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

# Database Mezzi
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
        "CRITRE_135.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5532, "lon": 9.6198, "tipo": "MSB", "sede": "CRI Treviglio"},
        "CRIHBG_154.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5940, "lon": 9.6910, "tipo": "MSB", "sede": "CRI Urgnano"},
        "CRIDAL_118.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6475, "lon": 9.6012, "tipo": "MSB", "sede": "CRI Dalmine"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

# Database Ospedali
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

database_mail = [
    {"mittente": "Milano Sport Eventi", "oggetto": "Richiesta Assistenza: Maratona Cittadina", "testo": "Richiesta copertura sanitaria per Maratona. Previsti 500 partecipanti.", "lat": 45.6960, "lon": 9.6670, "tipo": "ASSISTENZA SPORTIVA"},
    {"mittente": "Monza Circuit Staff", "oggetto": "Supporto Sanitario Gara GP", "testo": "Richiesta MSB fissa per turno prove libere circuito locale.", "lat": 45.5300, "lon": 9.6100, "tipo": "ASSISTENZA GARA"},
    {"mittente": "Arena Concerti BG", "oggetto": "Presidio Medico Concerto Rock", "testo": "Necessaria ambulanza per evento musicale serale in piazza.", "lat": 45.7042, "lon": 9.6622, "tipo": "EVENTO SPETTACOLO"}
]

# Variabili di Sessione
for key in ['missioni', 'notifiche_centrale', 'registro_radio', 'scrivania_selezionata', 'ruolo', 'mezzo_selezionato', 'turno_iniziato', 'richiesta_chiusura', 'evento_corrente', 'last_mission_time', 'time_mult', 'auto_mode', 'suono_riprodotto', 'log_chiamate']:
    if key not in st.session_state:
        if key in ['missioni']: st.session_state[key] = {}
        elif key in ['notifiche_centrale', 'registro_radio', 'log_chiamate']: st.session_state[key] = []
        elif key == 'time_mult': st.session_state[key] = 1.0
        elif key in ['auto_mode', 'turno_iniziato', 'richiesta_chiusura', 'suono_riprodotto']: st.session_state[key] = False
        elif key == 'last_mission_time': st.session_state[key] = time.time()
        else: st.session_state[key] = None

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    if is_eli: tempo_minuti += 2
    return round(distanza, 1), max(1, tempo_minuti)

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        mult = st.session_state.time_mult
        tempo_trascorso = now - creazione
        if tempo_trascorso < 30/mult:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, "STATO 1: Partenza da sede.")
        elif tempo_trascorso < 60/mult:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Arrivati sul posto.")
        elif tempo_trascorso >= 240/mult:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, "Mezzo LIBERO.")
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.missioni and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Bergamo", "via": "Piazza Vecchia", "lat": 45.7042, "lon": 9.6622},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]

scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore forte retrosternale.", "codice_reale": "ROSSO", "necessita_msa": True},
    {"sintomi": "Ragazzo caduto da moto, dolore gamba.", "codice_reale": "GIALLO", "necessita_msa": False},
]

# Generazione Chiamata a Tempo
tempo_necessario = 120 / st.session_state.time_mult
if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > tempo_necessario):
    if not st.session_state.evento_corrente:
        scelta_indirizzo = random.choice(database_indirizzi)
        scelta_clinica = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {
            "comune": scelta_indirizzo["comune"], "via": scelta_indirizzo["via"],
            "lat": scelta_indirizzo["lat"], "lon": scelta_indirizzo["lon"],
            "sintomi": scelta_clinica["sintomi"], "codice_reale": scelta_clinica["codice_reale"]
        }
        st.session_state.last_mission_time = time.time()
        st.session_state.suono_riprodotto = False

# ==================== INTERFACCIA OPERATIVA ====================
col_titolo, col_orologio = st.columns([3, 1])
with col_titolo: st.title(f"🚑 SOREU Alpina - {st.session_state.utente_connesso}")
with col_orologio: st.metric(label="🕒 Orario", value=datetime.now().strftime("%H:%M:%S"))

if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione")
    c1, c2, c3 = st.columns(3)
    if c1.button("🖥️ Scrivania 1", use_container_width=True): st.session_state.scrivania_selezionata = 1; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🖥️ Scrivania 2", use_container_width=True): st.session_state.scrivania_selezionata = 2; st.session_state.ruolo = "centrale"; st.rerun()
    if c3.button("🚑 Mezzo Esterno", use_container_width=True): st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"Utente: **{st.session_state.utente_connesso}**")
        if st.session_state.utente_connesso == 'admin':
            with st.expander("🛠️ Admin: Nuovi Utenti"):
                nu = st.text_input("User ID").lower()
                np = st.text_input("PW Provv.", type="password")
                if st.button("SALVA UTENTE"):
                    if aggiungi_nuovo_utente_db(nu, np): st.success("Creato!")
        
        st.divider()
        st.session_state.auto_mode = st.toggle("🤖 Automazione", value=st.session_state.auto_mode)
        vel = st.radio("Velocità", ["Normale", "2X", "5X"])
        st.session_state.time_mult = 1.0 if vel == "Normale" else (2.0 if vel == "2X" else 5.0)
        if st.button("🚪 LOGOUT"):
            st.session_state.utente_connesso = None
            st.rerun()

    # --- CONTENUTO CENTRALE ---
    if st.session_state.ruolo == "centrale":
        tab_invio, tab_risorse, tab_ps = st.tabs(["📝 Nuove Missioni", "🚑 Stato Risorse", "🏥 PS"])
        with tab_invio:
            col_evento, col_mappa = st.columns([1.5, 2])
            with col_evento:
                if st.session_state.evento_corrente:
                    if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                    ev = st.session_state.evento_corrente
                    st.warning(f"📍 Target: {ev['via']}")
                    st.info(f"🗣️ {ev['sintomi']}")
                    mezzi_disp = [m for m, d in st.session_state.database_mezzi.items() if d["stato"]=="Libero in Sede"]
                    scelti = st.multiselect("Invia Mezzi:", mezzi_disp)
                    if st.button("🚀 DISPACHING"):
                        for m in scelti:
                            st.session_state.missioni[m] = {"target": ev['via'], "timestamp_creazione": time.time(), "ospedale_assegnato": "Osp. Papa Giovanni XXIII (BG)"}
                            st.session_state.database_mezzi[m]["stato"] = "1 - Partenza"
                        st.session_state.evento_corrente = None; st.rerun()
            with col_mappa:
                st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))
        
        with tab_risorse:
            st.dataframe(pd.DataFrame.from_dict(st.session_state.database_mezzi, orient='index'))

    # --- INTERFACCIA MEZZO ---
    elif st.session_state.ruolo == "mezzo":
        if st.session_state.mezzo_selezionato is None:
            scelta = st.selectbox("Seleziona mezzo:", list(st.session_state.database_mezzi.keys()))
            if st.button("Login"): st.session_state.mezzo_selezionato = scelta; st.rerun()
        else:
            mio = st.session_state.mezzo_selezionato
            st.header(f"📟 Terminale: {mio}")
            st.write(f"Stato: {st.session_state.database_mezzi[mio]['stato']}")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("🚨 1"): st.session_state.database_mezzi[mio]["stato"] = "1 - Partenza"; st.rerun()
            if c2.button("📍 2"): st.session_state.database_mezzi[mio]["stato"] = "2 - Arrivo"; st.rerun()
            if c4.button("🏁 4"): 
                st.session_state.database_mezzi[mio]["stato"] = "Libero in Sede"
                if mio in st.session_state.missioni: del st.session_state.missioni[mio]
                st.rerun()
