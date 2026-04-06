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
# 2. SCHERMATA LOGIN
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}: Imposta una nuova password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Errore nelle password (minimo 4 caratteri).")
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
# 3. FUNZIONI AGGIUNTIVE (ECG E LOGICA MEDICA)
# =========================================================
def genera_tracciato_ecg(ritmo="sinusale"):
    x = np.linspace(0, 10, 500)
    if ritmo == "sinusale":
        y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    elif ritmo == "tachicardia":
        y = np.sin(x * 2.8 * 2 * np.pi) + np.random.normal(0, 0.1, 500)
    else:
        y = np.random.normal(0, 0.02, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

# =========================================================
# 4. IL TUO CODICE ORIGINALE CON AGGIUNTE INTEGRATE
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

# 1. DATABASE MEZZI
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

# AGGIUNTA: SISTEMA CONSUMABILI
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {
        m: {"O2": 100, "Elettrodi": 20, "DPI": 50} for m in st.session_state.database_mezzi.keys()
    }

# AGGIUNTA: REPOSITORY ECG (Per tele-consulto)
if 'ecg_repository' not in st.session_state:
    st.session_state.ecg_repository = {}

# 2. DATABASE OSPEDALI
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

if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None; st.session_state.mezzo_selezionato = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'richiesta_chiusura' not in st.session_state: st.session_state.richiesta_chiusura = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False
if 'suono_riprodotto' not in st.session_state: st.session_state.suono_riprodotto = False
if 'log_chiamate' not in st.session_state: st.session_state.log_chiamate = []

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
    if tempo_minuti < 1: tempo_minuti = 1
    return round(distanza, 1), tempo_minuti

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        tempo_trascorso = now - creazione
        if tempo_trascorso < 30 / st.session_state.time_mult:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, f"STATO 1: Partenza da sede direzione luogo intervento.")
        elif tempo_trascorso < 60 / st.session_state.time_mult:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Arrivati sul luogo dell'evento.")
        elif tempo_trascorso >= 60 / st.session_state.time_mult and tempo_trascorso < 120 / st.session_state.time_mult:
            if not miss.get("richiesto_ospedale", False):
                st.session_state.missioni[m_nome]["richiesto_ospedale"] = True
        elif tempo_trascorso >= 120 / st.session_state.time_mult and tempo_trascorso < 180 / st.session_state.time_mult:
            if db[m_nome]["stato"] != "3 - Partenza per ospedale":
                db[m_nome]["stato"] = "3 - Partenza per ospedale"
        elif tempo_trascorso >= 240 / st.session_state.time_mult:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            st.session_state.inventario_mezzi[m_nome]["O2"] -= random.randint(5, 15)
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.missioni and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]
scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore forte retrosternale.", "codice_reale": "ROSSO", "patologia": "Sospetto IMA", "necessita_msa": True},
    {"sintomi": "Trauma motociclista, cosciente.", "codice_reale": "GIALLO", "patologia": "Trauma Arto", "necessita_msa": False},
]

if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > 120 / st.session_state.time_mult):
    if not st.session_state.evento_corrente:
        scelta_indirizzo = random.choice(database_indirizzi)
        scelta_clinica = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {**scelta_indirizzo, **scelta_clinica}
        st.session_state.last_mission_time = time.time()
        st.session_state.log_chiamate.append(f"{scelta_indirizzo['via']} ({scelta_indirizzo['comune']})")
        st.session_state.suono_riprodotto = False

col_titolo, col_orologio = st.columns([3, 1])
with col_titolo: st.title("🎧 SOREU Alpina - Sala Operativa")
with col_orologio: st.metric(label="🕒 Orario Reale", value=datetime.now().strftime("%H:%M:%S"))

# ==================== 1. SCHERMATA SELEZIONE SCRIVANIA ====================
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione di Lavoro")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🖥️ Scrivania 1 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 1; st.session_state.ruolo = "centrale"; st.rerun()
    with col_b:
        if st.button("🖥️ Scrivania 2 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 2; st.session_state.ruolo = "centrale"; st.rerun()
    with col_c:
        if st.button("🖥️ Scrivania 3 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 3; st.session_state.ruolo = "centrale"; st.rerun()
    st.divider()
    if st.button("🚑 Accedi come Equipaggio Mezzo (Esterno)", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    st.subheader(f"📍 Sei seduto alla **SCRIVANIA {st.session_state.scrivania_selezionata}**")
    if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

else:
    with st.sidebar:
        st.write(f"Ruolo: **{st.session_state.ruolo.upper()}**")
        if st.button("⬅️ Cambia Ruolo"): st.session_state.scrivania_selezionata = None; st.rerun()
        st.divider()
        if st.button("🛑 CHIUDI TURNO"): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # ==================== 🎧 INTERFACCIA CENTRALE ====================
    if st.session_state.ruolo == "centrale":
        tab_invio, tab_risorse, tab_ps = st.tabs(["📝 Nuove Missioni", "🚑 Stato Risorse", "🏥 Monitoraggio PS"])
        
        with tab_invio:
            col_evento, col_mappa = st.columns([1.5, 2])
            with col_evento:
                if st.session_state.evento_corrente:
                    if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                    ev = st.session_state.evento_corrente
                    st.warning(f"📍 Target: {ev['via']}, {ev['comune']}")
                    st.info(f"🗣️ Sintomi: {ev['sintomi']}")
                    codice_scelto = st.selectbox("Assegna Codice", ["ROSSO", "GIALLO", "VERDE"])
                    mezzi_calcolo = [{"Mezzo": n, "Tempo (min)": calcola_distanza_e_tempo(d["lat"], d["lon"], ev["lat"], ev["lon"])[1]} for n, d in st.session_state.database_mezzi.items() if d["stato"] == "Libero in Sede"]
                    if mezzi_calcolo:
                        m_scelto = st.selectbox("Seleziona Mezzo", [m["Mezzo"] for m in mezzi_calcolo])
                        osp_selezionato = st.selectbox("Ospedale", list(st.session_state.database_ospedali.keys()))
                        if st.button("🚀 INVIA"):
                            st.session_state.database_mezzi[m_scelto]["stato"] = "In Missione"
                            st.session_state.missioni[m_scelto] = {"target": ev['via'], "timestamp_creazione": time.time(), "ospedale_assegnato": osp_selezionato, "patologia": ev['patologia']}
                            st.session_state.evento_corrente = None; st.rerun()
                else: st.info("In attesa di chiamata...")
            
            with col_mappa:
                st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))
                st.text_area("Registro Radio", "\n".join(st.session_state.registro_radio[:10]), height=150)

        with tab_risorse:
            for m, d in st.session_state.database_mezzi.items():
                with st.expander(f"🚑 {m} - {d['stato']}"):
                    st.write(f"O2: {st.session_state.inventario_mezzi[m]['O2']}%")
                    if m in st.session_state.ecg_repository:
                        st.line_chart(st.session_state.ecg_repository[m], x="Tempo", y="mV")

        with tab_ps:
            for osp, dati in st.session_state.database_ospedali.items():
                st.write(f"**{osp}** ({dati['pazienti']}/{dati['max']})")
                st.progress(dati["pazienti"]/dati["max"])

    # ==================== 🚑 INTERFACCIA MEZZO ====================
    elif st.session_state.ruolo == "mezzo":
        if st.session_state.mezzo_selezionato is None:
            st.session_state.mezzo_selezionato = st.selectbox("Seleziona mezzo:", list(st.session_state.database_mezzi.keys()))
            if st.button("Login"): st.rerun()
        else:
            mio_mezzo = st.session_state.mezzo_selezionato
            inv = st.session_state.inventario_mezzi[mio_mezzo]
            col_s, col_scheda = st.columns([1, 1.5])
            
            with col_s:
                st.header(f"📟 {mio_mezzo}")
                st.write(f"O2: {inv['O2']}% | Elettrodi: {inv['Elettrodi']}")
                if st.button("🚨 STATO 1"): st.session_state.database_mezzi[mio_mezzo]["stato"] = "1 - Partenza da sede"; st.rerun()
                if st.button("📍 STATO 2"): st.session_state.database_mezzi[mio_mezzo]["stato"] = "2 - Arrivato su posto"; st.rerun()
                if st.button("🏁 CHIUDI"): 
                    st.session_state.database_mezzi[mio_mezzo]["stato"] = "Libero in Sede"
                    if mio_mezzo in st.session_state.missioni: del st.session_state.missioni[mio_mezzo]
                    st.rerun()
            
            with col_scheda:
                if mio_mezzo in st.session_state.missioni:
                    st.subheader("🩺 Valutazione Clinica")
                    fc = st.slider("FC", 30, 180, 80)
                    if st.button("📉 ESEGUI ECG", type="primary"):
                        if inv['Elettrodi'] >= 4:
                            st.session_state.inventario_mezzi[mio_mezzo]['Elettrodi'] -= 4
                            ritmo = "sinusale" if fc < 100 else "tachicardia"
                            st.session_state.ecg_repository[mio_mezzo] = genera_tracciato_ecg(ritmo)
                            st.rerun()
                    if mio_mezzo in st.session_state.ecg_repository:
                        st.line_chart(st.session_state.ecg_repository[mio_mezzo], x="Tempo", y="mV")
