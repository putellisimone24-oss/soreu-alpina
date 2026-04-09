import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE E STATO INIZIALE
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
            ('simone.marinoni', 'simone', 1, 'Operatore'),
            ('andrea.giuliano', 'andrea', 1, 'Operatore')
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

# Inizializzazione DB
init_db()

# Configurazione Pagina
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide", initial_sidebar_state="expanded")

# Inizializzazione variabili di sessione (PROTEZIONE CRASH)
if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []
if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'mezzo_selezionato' not in st.session_state: st.session_state.mezzo_selezionato = None

# =========================================================
# 2. LOGIN E SICUREZZA
# =========================================================
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
# 3. GESTIONE UTENTI (SOLO ADMIN)
# =========================================================
def interfaccia_admin_gestione():
    st.markdown("### 🛠️ Gestione Accessi Operatori")
    conn = sqlite3.connect('centrale.db')
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Aggiungi nuovo account**")
        nuovo_u = st.text_input("Username (es: nome.cognome)", key="add_u").lower().strip()
        nuova_p = st.text_input("Password provvisoria", type="password", key="add_p")
        if st.button("Registra Operatore"):
            if nuovo_u and nuova_p:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO utenti VALUES (?,?,1,'Operatore')", (nuovo_u, nuova_p))
                    conn.commit()
                    st.success(f"Utente {nuovo_u} creato!")
                    st.rerun()
                except: st.error("L'utente esiste già.")
    
    with col2:
        st.write("**Rimuovi account esistente**")
        df_u = pd.read_sql_query("SELECT username FROM utenti WHERE username != 'admin'", conn)
        utente_del = st.selectbox("Seleziona utente da eliminare", df_u['username'].tolist() if not df_u.empty else ["Nessun utente"])
        if st.button("Elimina Definitivamente", type="primary"):
            if utente_del and utente_del != "Nessun utente":
                c = conn.cursor()
                c.execute("DELETE FROM utenti WHERE username=?", (utente_del,))
                conn.commit()
                st.success("Utente rimosso.")
                st.rerun()
    conn.close()

# =========================================================
# 4. SELEZIONE POSTAZIONE
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.title(f"Benvenuto, {st.session_state.utente_connesso.upper()}")
    
    # Se è admin, mostra il pannello di gestione prima delle scrivanie
    if st.session_state.utente_connesso == 'admin':
        with st.expander("⚙️ PANNELLO GESTIONE ACCOUNT"):
            interfaccia_admin_gestione()
    
    st.subheader("🖥️ Seleziona Postazione Operativa")
    cols = st.columns(3)
    for i in range(1, 10):
        with cols[(i-1)%3]:
            nome_desk = "SALA OPERATIVA - ADMIN" if st.session_state.utente_connesso == "admin" else f"SALA OPERATIVA - DESK {i}"
            if st.button(f"🖥️ {nome_desk}", use_container_width=True):
                st.session_state.scrivania_selezionata = nome_desk
                st.session_state.ruolo = "centrale"
                st.rerun()
    st.divider()
    if st.button("🚑 ACCEDI COME EQUIPAGGIO MEZZO", use_container_width=True):
        st.session_state.scrivania_selezionata = "EQUIPAGGIO"; st.session_state.ruolo = "mezzo"; st.rerun()
    st.stop()

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
                db[m_nome]["stato"] = "3 - Partenza per ospedale"
                destinazione = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                aggiungi_log_radio(m_nome, f"STATO 3: Paziente a bordo. Direzione {destinazione}.")
        elif tempo_trascorso >= fase_stato_4 and tempo_trascorso < durata_totale:
            if db[m_nome]["stato"] != "Arrivati in Ospedale":
                db[m_nome]["stato"] = "Arrivati in Ospedale"
                destinazione = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                aggiungi_log_radio(m_nome, f"Arrivati a destinazione presso {destinazione}.")
        elif tempo_trascorso >= durata_totale:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, f"Terminato scarico paziente. Mezzo LIBERO.")
            dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
            if dest in st.session_state.database_ospedali:
                if st.session_state.database_ospedali[dest]["pazienti"] < st.session_state.database_ospedali[dest]["max"]:
                    st.session_state.database_ospedali[dest]["pazienti"] += 1
                else: st.session_state.notifiche_centrale.append(f"⚠️ {dest} SATURO!")
            voci_da_rimuovere.append(m_nome)
            
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.missioni and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

# DATABASE EVENTI CLINICI
database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Bergamo", "via": "Piazza Vecchia", "lat": 45.7042, "lon": 9.6622},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
    {"comune": "Caravaggio", "via": "Piazza del Santuario 1", "lat": 45.5000, "lon": 9.6410},
    {"comune": "Dalmine", "via": "Via Guzzanica 5", "lat": 45.6470, "lon": 9.6100},
]

scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore forte retrosternale che irradia al braccio sinistro da 20 minuti.", "codice_reale": "ROSSO", "patologia": "Sospetto Infarto (IMA)", "necessita_msa": True},
    {"sintomi": "Ragazzo caduto da moto, cosciente, dolore lancinante alla gamba destra con deformità.", "codice_reale": "GIALLO", "patologia": "Trauma Arto Inferiore", "necessita_msa": False},
    {"sintomi": "Bambino di 4 anni con febbre a 39.5 e convulsioni in atto, i genitori sono nel panico.", "codice_reale": "ROSSO", "patologia": "Convulsione Febbrile", "necessita_msa": True},
    {"sintomi": "Anziana scivolata in casa, impossibilitata ad alzarsi, riferisce lieve dolore all'anca.", "codice_reale": "VERDE", "patologia": "Caduta in casa", "necessita_msa": False},
    {"sintomi": "Paziente trovato a terra incosciente, respiro agonico (gasping). Chiamante esegue massaggio.", "codice_reale": "ROSSO", "patologia": "Arresto Cardiaco", "necessita_msa": True}
]

tempo_base = 120
tempo_necessario = tempo_base / st.session_state.time_mult
if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > tempo_necessario):
    if not st.session_state.evento_corrente:
        scelta_indirizzo = random.choice(database_indirizzi)
        scelta_clinica = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {
            "comune": scelta_indirizzo["comune"], "via": scelta_indirizzo["via"],
            "lat": scelta_indirizzo["lat"], "lon": scelta_indirizzo["lon"],
            "sintomi": scelta_clinica["sintomi"], "codice_reale": scelta_clinica["codice_reale"],
            "necessita_msa": scelta_clinica["necessita_msa"]
        }
        st.session_state.last_mission_time = time.time()
        st.session_state.log_chiamate.append(f"{scelta_indirizzo['via']} ({scelta_indirizzo['comune']})")
        st.session_state.suono_riprodotto = False

# INTESTAZIONE
col_titolo, col_orologio = st.columns([3, 1])
with col_titolo: st.title("🎧 SOREU Alpina - Sala Operativa")
with col_orologio: st.metric(label="🕒 Orario Reale", value=datetime.now().strftime("%H:%M:%S"))

# ==================== 1. SCHERMATA SELEZIONE SCRIVANIA ====================
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione di Lavoro")
    st.write("Scegli una scrivania libera per accedere al sistema.")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🖥️ Scrivania 1 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 1; st.session_state.ruolo = "centrale"; st.rerun()
        if st.button("🖥️ Scrivania 4 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 4; st.session_state.ruolo = "centrale"; st.rerun()
    with col_b:
        if st.button("🖥️ Scrivania 2 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 2; st.session_state.ruolo = "centrale"; st.rerun()
        if st.button("🖥️ Scrivania 5 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 5; st.session_state.ruolo = "centrale"; st.rerun()
    with col_c:
        if st.button("🖥️ Scrivania 3 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 3; st.session_state.ruolo = "centrale"; st.rerun()
        if st.button("🖥️ Scrivania 6 (Libera)", use_container_width=True): st.session_state.scrivania_selezionata = 6; st.session_state.ruolo = "centrale"; st.rerun()
        
    st.divider()
    if st.button("🚑 Accedi come Equipaggio Mezzo (Esterno)", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    st.markdown("---")
    st.subheader(f"📍 Sei seduto alla **SCRIVANIA {st.session_state.scrivania_selezionata}**")
    st.info("ℹ️ Il software è pronto. Conferma l'inizio del turno per abilitare le linee telefoniche e ricevere le chiamate.")
    
    if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.session_state.last_mission_time = time.time(); st.rerun()
            
    if st.button("⬅️ Torna alla selezione"):
        st.session_state.scrivania_selezionata = None; st.session_state.ruolo = None; st.rerun()

else:
    # --- BARRA LATERALE ---
    if st.session_state.scrivania_selezionata == "MEZZO":
        st.sidebar.markdown("### Postazione: **EQUIPAGGIO**")
    else:
        st.sidebar.markdown(f"### 🖥️ Scrivania: **{st.session_state.scrivania_selezionata}**")
    
    # 🔄 PULSANTE CAMBIO RUOLO LIBERO
    if st.sidebar.button("⬅️ Cambia Ruolo", use_container_width=True):
        st.session_state.scrivania_selezionata = None
        st.session_state.ruolo = None
        st.session_state.mezzo_selezionato = None
        st.rerun()
        
    st.sidebar.divider()
    
    # 🛑 PULSANTE CHIUDI TURNO (OPZIONE FINALE)
    if not st.session_state.richiesta_chiusura:
        if st.sidebar.button("🛑 CHIUDI TURNO", type="secondary", use_container_width=True):
            st.session_state.richiesta_chiusura = True; st.rerun()
    else:
        st.sidebar.warning("Vuoi resettare tutto e chiudere il turno definitivamente?")
        col_c1, col_c2 = st.sidebar.columns(2)
        with col_c1:
            if st.button("✔️ Sì", type="primary", use_container_width=True):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
        with col_c2:
            if st.button("❌ No", use_container_width=True):
                st.session_state.richiesta_chiusura = False; st.rerun()

    st.sidebar.divider()

    # ==================== 🎧 INTERFACCIA CENTRALE ====================
    if st.session_state.ruolo == "centrale":
        
        with st.sidebar.expander("📊 APRI DASHBOARD AVANZATA", expanded=False):
            st.subheader("📩 Posta in Arrivo")
            selected_mail_idx = st.radio("Seleziona Mail:", range(len(database_mail)), format_func=lambda x: f"📧 {database_mail[x]['mittente']}")
            mail = database_mail[selected_mail_idx]
            st.text_area(label="Contenuto Mail", value=f"{mail['testo']}", height=100, disabled=True)
            
            if st.button("📅 Gestisci questo Evento", use_container_width=True):
                st.session_state.evento_corrente = {
                    "comune": mail["mittente"], "via": mail["tipo"], "lat": mail["lat"], "lon": mail["lon"],
                    "sintomi": "Richiesta assistenza programmata da mail.", "codice_reale": "VERDE", "necessita_msa": False
                }
                st.toast(f"Richiesta mail caricata!", icon="✉️"); st.rerun()

            st.divider()
            st.subheader("📞 Ultime Chiamate")
            if st.session_state.log_chiamate:
                for c in reversed(st.session_state.log_chiamate[-3:]): st.caption(f"☎️ {c}")
            else: st.caption("Nessuna chiamata.")

        st.sidebar.subheader("🕹️ Opzioni di Gioco")
        st.session_state.auto_mode = st.sidebar.toggle("🤖 Automatizza Equipaggi", value=st.session_state.auto_mode)
        
        st.sidebar.subheader("⏱️ Cadenza Chiamate")
        vel = st.sidebar.radio("Seleziona velocità", ["Normale", "2X", "5X", "10X"])
        st.session_state.time_mult = 1.0 if vel == "Normale" else (2.0 if vel == "2X" else (5.0 if vel == "5X" else 10.0))
        
        if st.session_state.notifiche_centrale:
            for notifica in st.session_state.notifiche_centrale: st.toast(notifica, icon="🚑")
            st.session_state.notifiche_centrale = []
            
        tab_invio, tab_risorse, tab_ps = st.tabs(["📝 Nuove Missioni", "🚑 Stato Risorse", "🏥 Monitoraggio PS"])
        
        with tab_invio:
            col_evento, col_mappa = st.columns([1.5, 2])
            with col_evento:
                st.header("📋 Ricezione Chiamate")
                if st.button("🔔 Forza Generazione Chiamata", type="primary", use_container_width=True):
                    scelta_indirizzo = random.choice(database_indirizzi)
                    scelta_clinica = random.choice(scenari_clinici)
                    st.session_state.evento_corrente = {
                        "comune": scelta_indirizzo["comune"], "via": scelta_indirizzo["via"],
                        "lat": scelta_indirizzo["lat"], "lon": scelta_indirizzo["lon"],
                        "sintomi": scelta_clinica["sintomi"], "codice_reale": scelta_clinica["codice_reale"],
                        "necessita_msa": scelta_clinica["necessita_msa"]
                    }
                    st.session_state.log_chiamate.append(f"{scelta_indirizzo['via']} ({scelta_indirizzo['comune']})")
                    st.session_state.suono_riprodotto = False; st.rerun()
                
                st.divider()
                
                if st.session_state.evento_corrente:
                    if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                    ev = st.session_state.evento_corrente
                    
                    st.warning(f"📍 Target: {ev['via']}, {ev['comune']}")
                    st.info(f"🗣️ **Sintomi Riferiti:** {ev['sintomi']}")
                    
                    st.subheader("🧠 Valutazione Operatore")
                    codice_scelto = st.selectbox("Assegna Codice di Gravità", ["ROSSO", "GIALLO", "VERDE"])
                    
                    mezzi_calcolo = []
                    for nome, dati in st.session_state.database_mezzi.items():
                        if dati["stato"] == "Libero in Sede":
                            dist, tempo = calcola_distanza_e_tempo(dati["lat"], dati["lon"], ev["lat"], ev["lon"], is_eli=(dati["tipo"] == "ELI"))
                            mezzi_calcolo.append({"Mezzo": nome, "Tipo": dati["tipo"], "Sede": dati["sede"], "Tempo (min)": tempo})
                    
                    if mezzi_calcolo:
                        df_calcolo = pd.DataFrame(mezzi_calcolo).sort_values(by="Tempo (min)")
                        st.dataframe(df_calcolo, hide_index=True, use_container_width=True)
                        
                        mezzi_scelti = st.multiselect("Seleziona Mezzi da inviare", df_calcolo["Mezzo"].tolist())
                        osp_selezionato = st.selectbox("Pre-allerta Ospedale", list(st.session_state.database_ospedali.keys()))
                        
                        if st.button("🚀 INVIA MEZZI", type="primary", use_container_width=True) and mezzi_scelti:
                            if codice_scelto != ev['codice_reale']:
                                st.toast(f"⚠️ Triage non ottimale! Il protocollo suggeriva codice {ev['codice_reale']}.", icon="⚠️")
                            else:
                                st.toast("✔️ Ottimo Triage! Codice coerente con i sintomi.", icon="👍")
                                
                            for m_scelto in mezzi_scelti:
                                if not st.session_state.auto_mode:
                                    st.session_state.database_mezzi[m_scelto]["stato"] = "1 - Partenza da sede"; st.session_state.database_mezzi[m_scelto]["colore"] = "🟡"
                                    aggiungi_log_radio(m_scelto, "STATO 1: Partenza da sede direzione luogo intervento.")
                                st.session_state.missioni[m_scelto] = {
                                    "target": f"{ev['via']}, {ev['comune']}", "lat": ev['lat'], "lon": ev['lon'],
                                    "codice": codice_scelto, "ospedale_assegnato": osp_selezionato,
                                    "timestamp_creazione": time.time(), "richiesto_ospedale": False,
                                    "patologia": ev.get("sintomi", "Generica")
                                }
                            st.session_state.evento_corrente = None; st.rerun()
                    else: st.error("Nessun mezzo disponibile!")
                else: st.info("In attesa di chiamata da NUE 112...")
                    
            with col_mappa:
                st.header("🗺️ Mappa Area Alpina")
                punti_mappa = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    for i in range(0, 360, 45):
                        punti_mappa.append({"lat": ev["lat"] + 0.005 * math.cos(math.radians(i)), "lon": ev["lon"] + 0.005 * math.sin(math.radians(i))})
                        
                if punti_mappa: st.map(pd.DataFrame(punti_mappa), zoom=9)
                
                st.subheader("📻 Registro Radio SOREU")
                if st.session_state.registro_radio:
                    box_testo = "\n".join(st.session_state.registro_radio[:15])
                    st.text_area(label="Comunicazioni Voce", value=box_testo, height=150, disabled=True)
                
                st.subheader("📋 Missioni in Corso")
                if st.session_state.missioni:
                    for m, dati in st.session_state.missioni.items():
                        c_m, c_o = st.columns([2, 1])
                        with c_m: st.write(f"🚑 **{m}** -> {dati['target']} ({st.session_state.database_mezzi[m]['stato']})")
                        with c_o:
                            nuovo_osp = st.selectbox(f"Osp. per {m}", list(st.session_state.database_ospedali.keys()), key=f"sel_osp_{m}")
                            if nuovo_osp != dati.get("ospedale_confermato", dati["ospedale_assegnato"]):
                                st.session_state.missioni[m]["ospedale_confermato"] = nuovo_osp; st.toast(f"Ospedale aggiornato per {m} -> {nuovo_osp}")
                else: st.caption("Nessuna missione in corso.")
        
        with tab_risorse:
            st.header("🚑 Stato Risorse Territoriali")
            for m, d in st.session_state.database_mezzi.items(): st.write(f"**{m}** ({d['tipo']}): {d['stato']}")
                
        with tab_ps:
            st.header("🏥 Saturazione Pronto Soccorso")
            for osp, dati in st.session_state.database_ospedali.items():
                col_info, col_azione = st.columns([3, 1])
                with col_info:
                    st.write(f"**{osp}** ({dati['pazienti']} / {dati['max']})")
                    st.progress((dati["pazienti"] / dati["max"]))
                with col_azione:
                    if st.button(f"Libera Posto", key=f"dim_{osp}"):
                        if dati["pazienti"] > 0: st.session_state.database_ospedali[osp]["pazienti"] -= 1; st.rerun()

    # ==================== 🚑 INTERFACCIA MEZZO ====================
    elif st.session_state.ruolo == "mezzo":
        if st.session_state.auto_mode: st.warning("⚠️ La modalità AUTOMATICA è attiva.")
        
        if st.session_state.mezzo_selezionato is None:
            st.subheader("Identificazione Equipaggio")
            scelta = st.radio("Seleziona mezzo:", list(st.session_state.database_mezzi.keys()))
            if st.button("Login", use_container_width=True): st.session_state.mezzo_selezionato = scelta; st.rerun()
        else:
            mio_mezzo = st.session_state.mezzo_selezionato
            dati_mezzo = st.session_state.database_mezzi[mio_mezzo]
            
            # Layout a due colonne per l'equipaggio
            col_stati, col_scheda = st.columns([1, 1.5])
            
            with col_stati:
                st.header(f"📟 Terminale: {mio_mezzo}")
                st.write(f"Stato Attuale: **{dati_mezzo['stato']}**")
                
                st.divider()
                st.subheader("Pulsantiera Operativa")
                in_missione = mio_mezzo in st.session_state.missioni
                miss = st.session_state.missioni[mio_mezzo] if in_missione else None
                disabilita_manuale = st.session_state.auto_mode or not in_missione
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🚨 1 - Partenza Sede", use_container_width=True, disabled=disabilita_manuale):
                        dati_mezzo["stato"] = "1 - Partenza da sede"
                        aggiungi_log_radio(mio_mezzo, "STATO 1: Partenza da sede direzione luogo intervento."); st.rerun()
                    if st.button("🏥 3 - Partenza Ospedale", use_container_width=True, disabled=disabilita_manuale):
                        dati_mezzo["stato"] = "3 - Partenza per ospedale"
                        dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                        aggiungi_log_radio(mio_mezzo, f"STATO 3: Paziente a bordo. Direzione {dest}."); st.rerun()
                with c2:
                    if st.button("📍 2 - Arrivo Posto", use_container_width=True, disabled=disabilita_manuale):
                        dati_mezzo["stato"] = "2 - Arrivato su posto"
                        aggiungi_log_radio(mio_mezzo, "STATO 2: Arrivati sul luogo dell'evento."); st.rerun()
                    if st.button("🏁 4 - Arrivo Ospedale", type="primary", use_container_width=True, disabled=disabilita_manuale):
                        dati_mezzo["stato"], dati_mezzo["colore"] = "Libero in Sede", "🟢"
                        aggiungi_log_radio(mio_mezzo, "STATO 4: Arrivati a destinazione. Mezzo LIBERO.")
                        dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                        if dest in st.session_state.database_ospedali: st.session_state.database_ospedali[dest]["pazienti"] += 1
                        del st.session_state.missioni[mio_mezzo]; st.rerun()
            
            with col_scheda:
                st.header("📋 Scheda Paziente")
                if in_missione and dati_mezzo["stato"] in ["2 - Arrivato su posto", "3 - Partenza per ospedale"]:
                    st.info(f"🎯 **Target:** {miss['target']}\n\n🗣️ **Note Centrale:** {miss.get('patologia','N/D')}")
                    
                    st.subheader("🩺 Inserimento Parametri Vitali")
                    pa_sistolica = st.slider("Pressione Sistolica (PA)", 50, 200, 120)
                    freq_card = st.slider("Frequenza Cardiaca (FC)", 30, 180, 80)
                    sat_o2 = st.slider("Saturazione O2 (%)", 70, 100, 98)
                    scala_gcs = st.selectbox("Livello di Coscienza (GCS)", ["15 - Sveglio e Cosciente", "12/14 - Confuso/Sonnolento", "8 o meno - Coma / Non risponde"])
                    
                    pz_critico = (pa_sistolica < 90 or pa_sistolica > 180 or freq_card < 50 or freq_card > 120 or sat_o2 < 90 or "8 o meno" in scala_gcs)
                    
                    if pz_critico:
                        st.error("⚠️ ATTENZIONE: I parametri indicano un paziente INSTABILE!")
                        if st.button("📞 Richiedi Supporto Medica (MSA / ELI)", type="primary", use_container_width=True):
                            st.session_state.notifiche_centrale.append(f"🆘 {mio_mezzo} richiede AUTOMEDICA sul posto per parametri critici!")
                            aggiungi_log_radio(mio_mezzo, f"Centrale da {mio_mezzo}: Richiediamo supporto medico sul posto. Paziente non stabile.")
                            st.toast("Richiesta inviata in Centrale!", icon="🚨")
                    else:
                        st.success("Parametri accettabili per trasporto con MSB.")
                        if st.button("📑 Trasmetti Parametri e richiedi Ospedale", use_container_width=True):
                            st.session_state.notifiche_centrale.append(f"🩺 {mio_mezzo} comunica parametri: PA {pa_sistolica}, FC {freq_card}, Sat {sat_o2}%.")
                            aggiungi_log_radio(mio_mezzo, f"Centrale da {mio_mezzo}: Parametri trasmessi. Richiediamo conferma ospedale per ripartire.")
                            st.toast("Parametri inviati!", icon="✔️")
                
                elif in_missione and dati_mezzo["stato"] == "1 - Partenza da sede":
                    st.warning("Raggiungi il luogo dell'evento per sbloccare la scheda paziente.")
                    st.info(f"🚩 **Direzione:** {miss['target']}")
                else:
                    st.success("Nessun paziente a bordo. In attesa di missione.")
