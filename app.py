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
# 2. CONFIGURAZIONE E INIZIALIZZAZIONE SESSIONE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide", initial_sidebar_state="expanded")

# Inizializzazione variabili di stato se non presenti
defaults = {
    'utente_connesso': None, 'fase_cambio_pw': False, 'missioni': {}, 
    'notifiche_centrale': [], 'registro_radio': [], 'scrivania_selezionata': None,
    'ruolo': None, 'mezzo_selezionato': None, 'turno_iniziato': False,
    'evento_corrente': None, 'last_mission_time': time.time(), 'time_mult': 1.0,
    'auto_mode': False, 'suono_riprodotto': False, 'log_chiamate': [],
    'ecg_repository': {}, 'richiesta_chiusura': False
}
for key, value in defaults.items():
    if key not in st.session_state: st.session_state[key] = value

# DATABASE MEZZI REALI
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

# INVENTARIO CONSUMABILI
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {
        m: {"Ossigeno": 100, "Elettrodi": 25, "DPI": 40, "Farmaci": 10} for m in st.session_state.database_mezzi.keys()
    }

# OSPEDALI
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# =========================================================
# 3. LOGICA DI ACCESSO (LOGIN)
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Sistema Informativo Centrale")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}. Imposta una password sicura.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Le password non coincidono o sono troppo corte.")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("LOGIN", type="primary"):
            res = get_utente_db(u_in)
            if res and res[1] == p_in:
                if res[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("ID o Password errati.")
    st.stop()

# =========================================================
# 4. FUNZIONI DI SERVIZIO (ECG, AUDIO, LOGICA)
# =========================================================
def genera_tracciato_ecg(ritmo="sinusale"):
    x = np.linspace(0, 10, 1000)
    if ritmo == "sinusale":
        y = np.sin(x*1.2*2*np.pi) + 0.5*np.sin(x*2.4*2*np.pi) + np.random.normal(0,0.05,1000)
    elif ritmo == "tachicardia":
        y = np.sin(x*2.8*2*np.pi) + np.random.normal(0,0.1,1000)
    else: # Asistolia / Rumore
        y = np.random.normal(0, 0.05, 1000)
    return pd.DataFrame({"Tempo": x, "mV": y})

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
# 5. GENERAZIONE EVENTI E SCENARI
# =========================================================
database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Bergamo", "via": "Piazza Vecchia", "lat": 45.7042, "lon": 9.6622},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Caravaggio", "via": "Piazza del Santuario 1", "lat": 45.5000, "lon": 9.6410},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]
scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore forte retrosternale che irradia al braccio.", "codice": "ROSSO", "patologia": "Sospetto IMA", "msa": True},
    {"sintomi": "Bambino 4 anni, febbre alta e convulsioni in atto.", "codice": "ROSSO", "patologia": "Convulsione", "msa": True},
    {"sintomi": "Trauma stradale, motociclista a terra cosciente, dolore arto inf.", "codice": "GIALLO", "patologia": "Trauma", "msa": False},
    {"sintomi": "Anziana caduta in casa, probabile frattura femore.", "codice": "VERDE", "patologia": "Caduta", "msa": False},
]

if st.session_state.turno_iniziato:
    tempo_soglia = 120 / st.session_state.time_mult
    if (time.time() - st.session_state.last_mission_time > tempo_soglia) and not st.session_state.evento_corrente:
        addr = random.choice(database_indirizzi)
        clin = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {**addr, **clin}
        st.session_state.last_mission_time = time.time()
        st.session_state.suono_riprodotto = False

# =========================================================
# 6. INTERFACCIA UTENTE PRINCIPALE
# =========================================================

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚑 SOREU Alpina")
    st.write(f"Utente: **{st.session_state.utente_connesso}**")
    if st.session_state.scrivania_selezionata:
        if st.button("⬅️ TORNA AL MENU"):
            st.session_state.scrivania_selezionata = None
            st.rerun()
    st.divider()
    if st.button("🛑 CHIUDI SISTEMA"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- MENU SELEZIONE ---
if st.session_state.scrivania_selezionata is None:
    st.header("Seleziona Postazione di Lavoro")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🖥️ Centrale Operativa")
        for i in range(1, 4):
            if st.button(f"Scrivania {i}", use_container_width=True):
                st.session_state.scrivania_selezionata = i; st.session_state.ruolo = "centrale"; st.rerun()
    with c2:
        st.subheader("🚑 Operativo Territoriale")
        if st.button("Tablet Bordo Mezzo", type="primary", use_container_width=True):
            st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# --- INTERFACCIA CENTRALE ---
elif st.session_state.ruolo == "centrale":
    if not st.session_state.turno_iniziato:
        st.info("Sistema pronto. Inizia il turno per ricevere chiamate.")
        if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
            st.session_state.turno_iniziato = True; st.rerun()
    else:
        st.sidebar.subheader("🕹️ Controlli")
        st.session_state.time_mult = st.sidebar.select_slider("Velocità Simulazione", options=[1, 2, 5, 10], value=1)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📟 MISSIONI", "🗺️ MAPPA & RADIO", "🚑 FLOTTA", "🏥 OSPEDALI"])
        
        with tab1:
            if st.session_state.evento_corrente:
                if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                ev = st.session_state.evento_corrente
                st.error(f"🚨 NUOVA CHIAMATA NUE: {ev['codice']} - {ev['sintomi']}")
                st.write(f"📍 Posizione: {ev['via']}, {ev['comune']}")
                
                # Calcolo mezzi
                mezzi_calc = []
                for m, d in st.session_state.database_mezzi.items():
                    if d["stato"] == "Libero in Sede":
                        dist, t_m = calcola_distanza_e_tempo(d["lat"], d["lon"], ev["lat"], ev["lon"], (d["tipo"]=="ELI"))
                        mezzi_calc.append({"Mezzo": m, "Tipo": d["tipo"], "Tempo (min)": t_m})
                
                if mezzi_calc:
                    df_mezzi = pd.DataFrame(mezzi_calc).sort_values("Tempo (min)")
                    st.table(df_mezzi)
                    scelti = st.multiselect("Seleziona Mezzi da inviare:", df_mezzi["Mezzo"].tolist())
                    if st.button("🚀 INVIA"):
                        for m in scelti:
                            st.session_state.database_mezzi[m]["stato"] = "1 - Partenza da sede"
                            st.session_state.missioni[m] = {"target": ev['via'], "lat": ev['lat'], "lon": ev['lon'], "codice": ev['codice'], "clinica": ev['patologia']}
                            aggiungi_log_radio(m, f"Ricevuto, partiamo per {ev['comune']} codice {ev['codice']}.")
                        st.session_state.evento_corrente = None; st.rerun()
            else: st.info("In attesa di chiamate...")

        with tab2:
            c_map, c_log = st.columns([2, 1])
            with c_map:
                st.subheader("Mappa Area di Competenza")
                punti = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
                st.map(pd.DataFrame(punti), zoom=9)
            with c_log:
                st.subheader("📻 Registro Radio")
                st.text_area("Live Radio Log", "\n".join(st.session_state.registro_radio), height=400, disabled=True)

        with tab3:
            st.subheader("Monitoraggio Flotta e ECG")
            for m, d in st.session_state.database_mezzi.items():
                with st.expander(f"{d['colore']} {m} - {d['stato']}"):
                    col_i, col_e = st.columns([1, 2])
                    with col_i:
                        inv = st.session_state.inventario_mezzi[m]
                        st.write(f"O2: {inv['Ossigeno']}% | Elettrodi: {inv['Elettrodi']}")
                        st.progress(inv["Ossigeno"]/100)
                    with col_e:
                        if m in st.session_state.ecg_repository:
                            st.line_chart(st.session_state.ecg_repository[m], x="Tempo", y="mV", height=150)
                            st.caption("Ultimo ECG ricevuto per tele-consulto")
                        else: st.caption("Nessun ECG disponibile")

        with tab4:
            for osp, info in st.session_state.database_ospedali.items():
                st.write(f"**{osp}** ({info['pazienti']}/{info['max']})")
                st.progress(info['pazienti']/info['max'])
                if st.button(f"Svuota {osp}"): 
                    st.session_state.database_ospedali[osp]['pazienti'] = max(0, info['pazienti']-1); st.rerun()

# --- INTERFACCIA MEZZO ---
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        m_sel = st.selectbox("Identificativo Mezzo:", list(st.session_state.database_mezzi.keys()))
        if st.button("ACCEDI AL TABLET"):
            st.session_state.mezzo_selezionato = m_sel; st.rerun()
    else:
        m_id = st.session_state.mezzo_selezionato
        dati = st.session_state.database_mezzi[m_id]
        inv = st.session_state.inventario_mezzi[m_id]
        
        st.header(f"📟 Terminale di Bordo: {m_id}")
        
        col_stati, col_inv = st.columns([2, 1])
        with col_inv:
            st.subheader("📦 Riserve")
            st.write(f"Ossigeno: {inv['Ossigeno']}%")
            st.write(f"Elettrodi: {inv['Elettrodi']}")
            if st.button("Rifornisci"): 
                st.session_state.inventario_mezzi[m_id] = {"Ossigeno": 100, "Elettrodi": 25, "DPI": 40, "Farmaci": 10}; st.rerun()
        
        with col_stati:
            st.subheader(f"Stato Attuale: {dati['stato']}")
            in_miss = m_id in st.session_state.missioni
            
            c1, c2 = st.columns(2)
            if c1.button("🚨 PARTENZA", disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "1 - Partenza da sede"; st.rerun()
            if c2.button("📍 ARRIVO POSTO", disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "2 - Arrivato su posto"; st.rerun()
            if c1.button("🏥 PARTENZA OSP", disabled=not in_miss):
                st.session_state.database_mezzi[m_id]["stato"] = "3 - Partenza per ospedale"; st.rerun()
            if c2.button("🏁 CHIUDI", disabled=not in_miss, type="primary"):
                st.session_state.database_mezzi[m_id]["stato"] = "Libero in Sede"
                st.session_state.inventario_mezzi[m_id]["Ossigeno"] -= random.randint(5,15)
                del st.session_state.missioni[m_id]
                if m_id in st.session_state.ecg_repository: del st.session_state.ecg_repository[m_id]
                st.rerun()

        if in_miss:
            st.divider()
            st.subheader("🩺 Scheda Clinica")
            miss = st.session_state.missioni[m_id]
            st.write(f"**Target:** {miss['target']} | **Clinica:** {miss['clinica']}")
            
            pa = st.slider("PA Sistolica", 40, 200, 120)
            fc = st.slider("Freq. Cardiaca", 30, 180, 80)
            
            if st.button("📉 ESEGUI ECG", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[m_id]['Elettrodi'] -= 4
                    ritmo = "sinusale" if fc < 100 else "tachicardia"
                    st.session_state.ecg_repository[m_id] = genera_tracciato_ecg(ritmo)
                    aggiungi_log_radio(m_id, f"Trasmesso ECG. Parametri: PA {pa}, FC {fc}. Richiediamo Ospedale.")
                    st.rerun()
                else: st.error("Elettrodi esauriti!")
            
            if m_id in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[m_id], x="Tempo", y="mV")
