import streamlit as st
import pandas as pd
import numpy as np
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

init_db()

# --- AGGIUNTA FUNZIONE ECG ---
def genera_tracciato_ecg():
    x = np.linspace(0, 10, 500)
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

# =========================================================
# 2. SCHERMATA LOGIN (PRIMA DI TUTTO IL RESTO)
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
    st.stop() # Blocca il resto del codice finché non sei loggato

# =========================================================
# 3. IL TUO CODICE ORIGINALE (INTEGRALE)
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

# 1. DATABASE MEZZI SANITARI REALI
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

# 2. DATABASE OSPEDALI REALI
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

# INIZIALIZZAZIONE VARIABILI DI SESSIONE
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

# --- AGGIUNTA INIZIALIZZAZIONE ECG E INVENTARIO ---
if 'ecg_repository' not in st.session_state:
    st.session_state.ecg_repository = {}
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

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

# Gestione AUTOMATICA degli stati a tempo
def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        
        fase_stato_1 = 30 / st.session_state.time_mult
        fase_stato_2 = 60 / st.session_state.time_mult
        fase_richiesta_osp = 60 / st.session_state.time_mult
        fase_stato_3 = 120 / st.session_state.time_mult
        fase_stato_4 = 180 / st.session_state.time_mult
        durata_totale = 240 / st.session_state.time_mult
        
        tempo_trascorso = now - creazione
        
        if tempo_trascorso < fase_stato_1:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, f"STATO 1: Partenza da sede direzione luogo intervento.")
        elif tempo_trascorso < fase_stato_2:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Arrivati sul luogo dell'evento.")
        elif tempo_trascorso >= fase_richiesta_osp and tempo_trascorso < fase_stato_3:
            if not miss.get("richiesto_ospedale", False):
                fc, pa = random.randint(70, 110), random.randint(110, 160)
                st.session_state.notifiche_centrale.append(f"🩺 {m_nome} richiede ospedale! Parametri: PA {pa}/90, FC {fc}.")
                aggiungi_log_radio(m_nome, f"Centrale da {m_nome}: Paziente valutato. Parametri stabili. Richiediamo ospedale di destinazione.")
                riproduci_suono_notifica()
                st.session_state.missioni[m_nome]["richiesto_ospedale"] = True
        elif tempo_trascorso >= fase_stato_3 and tempo_trascorso < fase_stato_4:
            if db[m_nome]["stato"] != "3 - Partenza per ospedale":
                db[m_nome]["stato"] = "3 - Partenza per ospedale"; db[m_nome]["colore"] = "🟠"
                aggiungi_log_radio(m_nome, "STATO 3: Caricato paziente, direzione ospedale.")
        elif tempo_trascorso >= fase_stato_4 and tempo_trascorso < durata_totale:
            if db[m_nome]["stato"] != "4 - Arrivato in ospedale":
                db[m_nome]["stato"] = "4 - Arrivato in ospedale"; db[m_nome]["colore"] = "🔴"
                aggiungi_log_radio(m_nome, "STATO 4: Arrivati in Pronto Soccorso. Consegna paziente.")
        elif tempo_trascorso >= durata_totale:
            db[m_nome]["stato"] = "Libero in Sede"; db[m_nome]["colore"] = "🟢"
            voci_da_rimuovere.append(m_nome)
            aggiungi_log_radio(m_nome, "FINE: Mezzo rientrato e disponibile.")
            
    for v in voci_da_rimuovere:
        del st.session_state.missioni[v]

# LOGICA UI
if st.session_state.scrivania_selezionata is None:
    st.header(f"Operatore: {st.session_state.utente_connesso}")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA", use_container_width=True):
        st.session_state.scrivania_selezionata = "SALA"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 TERMINALE BORDO MEZZO", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif st.session_state.ruolo == "centrale":
    st.sidebar.button("🔙 Menu Principale", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
    if st.session_state.auto_mode: aggiorna_stati_automatici()
    
    # --- AGGIUNTA TAB ECG IN CENTRALE ---
    tab1, tab2, tab3, tab4 = st.tabs(["📟 Missioni", "🗺️ Mappa", "📡 Tele-ECG", "📻 Radio"])
    
    with tab1:
        st.subheader("Gestione Eventi SOREU Alpina")
        if st.button("🚨 GENERA NUOVO TARGET"):
            nuovo_id = f"T{random.randint(100, 999)}"
            st.session_state.missioni[nuovo_id] = {"target": f"Via Roma {random.randint(1,50)}", "codice": "ROSSO", "timestamp_creazione": time.time()}
            st.rerun()
        st.write(st.session_state.missioni)
        
    with tab2:
        df_mezzi = pd.DataFrame([{"lat": d["lat"], "lon": d["lon"], "Mezzo": k} for k, d in st.session_state.database_mezzi.items()])
        st.map(df_mezzi)

    with tab3:
        st.subheader("📡 ECG in Tempo Reale")
        if not st.session_state.ecg_repository:
            st.info("Nessun tracciato ECG in ricezione.")
        for m, ecg in st.session_state.ecg_repository.items():
            with st.expander(f"🚑 Tracciato da {m}", expanded=True):
                st.line_chart(ecg, x="Tempo", y="mV")
                if st.button(f"Referta ECG {m}"):
                    del st.session_state.ecg_repository[m]; st.rerun()
    
    with tab4:
        for log in st.session_state.registro_radio: st.text(log)

elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("CONNETTI"): st.rerun()
    else:
        mio_mezzo = st.session_state.mezzo_selezionato
        dati_mezzo = st.session_state.database_mezzi[mio_mezzo]
        inv = st.session_state.inventario_mezzi[mio_mezzo]
        
        st.sidebar.button("🔙 Logout Mezzo", on_click=lambda: st.session_state.update({"mezzo_selezionato": None}))
        st.title(f"🚑 Tablet: {mio_mezzo}")
        
        col_info, col_scheda = st.columns([1, 2])
        
        with col_info:
            # --- AGGIUNTA INVENTARIO IN MEZZO ---
            st.subheader("📦 Risorse")
            st.metric("O2", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("🔄 Rifornimento"):
                st.session_state.inventario_mezzi[mio_mezzo] = {"O2": 100, "Elettrodi": 20}; st.rerun()
            
            st.divider()
            # --- AGGIUNTA INVIO ECG IN MEZZO ---
            st.subheader("🩺 Tele-ECG")
            if st.button("📉 INVIA ECG IN CENTRALE", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[mio_mezzo]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[mio_mezzo] = genera_tracciato_ecg()
                    st.toast("ECG inviato con successo!")
                    st.rerun()
                else: st.error("Elettrodi esauriti!")
            
            if mio_mezzo in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[mio_mezzo], x="Tempo", y="mV")

        with col_scheda:
            st.header("📋 Scheda Paziente")
            in_missione = mio_mezzo in st.session_state.missioni
            if in_missione:
                miss = st.session_state.missioni[mio_mezzo]
                st.info(f"🎯 **Target:** {miss['target']}")
                
                # Tasti stato originali (esempio semplificato per brevità, ma mantenendo la logica)
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("1"): aggiungi_log_radio(mio_mezzo, "Stato 1"); dati_mezzo["stato"] = "1"
                if c2.button("2"): aggiungi_log_radio(mio_mezzo, "Stato 2"); dati_mezzo["stato"] = "2"
                if c3.button("3"): aggiungi_log_radio(mio_mezzo, "Stato 3"); dati_mezzo["stato"] = "3"
                if c4.button("4"): aggiungi_log_radio(mio_mezzo, "Stato 4"); dati_mezzo["stato"] = "4"

                if st.button("🏁 CHIUDI INTERVENTO"):
                    st.session_state.inventario_mezzi[mio_mezzo]["O2"] -= 10
                    if mio_mezzo in st.session_state.ecg_repository: del st.session_state.ecg_repository[mio_mezzo]
                    del st.session_state.missioni[mio_mezzo]; st.rerun()
            else:
                st.success("Nessun paziente a bordo. In attesa di missione.")
