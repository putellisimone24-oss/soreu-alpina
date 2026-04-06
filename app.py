import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. CONFIGURAZIONE PAGINA E SISTEMA DI SICUREZZA
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

# Database utenti (Puoi aggiungere altri utenti qui)
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin123", "ruolo": "Centrale"},
        "mario.rossi": {"pw": "118", "ruolo": "Operatore"}
    }

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None

# --- LOGICA DI LOGIN ---
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Accesso Riservato")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("Login Operatore")
        u = st.text_input("Username").lower()
        p = st.text_input("Password", type="password")
        if st.button("ACCEDI AL SISTEMA", type="primary", use_container_width=True):
            if u in st.session_state.utenti_db and st.session_state.utenti_db[u]["pw"] == p:
                st.session_state.utente_connesso = u
                st.rerun()
            else:
                st.error("Credenziali non valide. Riprova.")
    with col_r:
        st.info("Benvenuto nel simulatore SOREU Alpina. Inserisci le tue credenziali per gestire la centrale operativa o i mezzi di soccorso.")
    st.stop() # Blocca l'esecuzione qui finché non c'è il login

# =========================================================
# 2. IL TUO SIMULATORE COMPLETO (Sbloccato dopo il Login)
# =========================================================

# --- FUNZIONI AUDIO E CALCOLO ---
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    distanza = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    velocita = 220.0 if is_eli else 45.0
    tempo = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo)

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# --- DATABASE MEZZI ---
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

# --- DATABASE OSPEDALI ---
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# Inizializzazione variabili sessione
for key in ['missioni', 'notifiche_centrale', 'registro_radio', 'log_chiamate']:
    if key not in st.session_state: st.session_state[key] = [] if 'notifiche' in key or 'registro' in key or 'log' in key else {}

if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None; st.session_state.mezzo_selezionato = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False

# --- LOGICA AUTOMATICA ---
def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        tempo_trascorso = now - miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        if tempo_trascorso < 30/st.session_state.time_mult:
            db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
        elif tempo_trascorso < 120/st.session_state.time_mult:
            db[m_nome]["stato"] = "2 - Arrivato su posto"
        elif tempo_trascorso >= 240/st.session_state.time_mult:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode: aggiorna_stati_automatici()

# --- BARRA LATERALE (Logout e Stato) ---
st.sidebar.title(f"👤 {st.session_state.utente_connesso}")
if st.sidebar.button("🚪 LOGOUT", use_container_width=True):
    st.session_state.utente_connesso = None
    st.rerun()

st.sidebar.divider()

# --- SELEZIONE POSTAZIONE ---
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione Operativa")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🖥️ Scrivania 1", use_container_width=True): 
            st.session_state.scrivania_selezionata = 1; st.session_state.ruolo = "centrale"; st.rerun()
    with c2:
        if st.button("🖥️ Scrivania 2", use_container_width=True): 
            st.session_state.scrivania_selezionata = 2; st.session_state.ruolo = "centrale"; st.rerun()
    with c3:
        if st.button("🚑 Mezzo Esterno", use_container_width=True): 
            st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    st.info(f"Postazione {st.session_state.scrivania_selezionata} pronta.")
    if st.button("🔴 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

else:
    # --- INTERFACCIA OPERATIVA FINALE ---
    col_t, col_o = st.columns([3, 1])
    with col_t: st.header(f"📟 Centrale SOREU - Postazione {st.session_state.scrivania_selezionata}")
    with col_o: st.metric("Orario", datetime.now().strftime("%H:%M:%S"))

    tab_centrale, tab_mappa, tab_ospedali = st.tabs(["📝 Gestione Chiamate", "🗺️ Mappa Territorio", "🏥 Stato PS"])

    with tab_centrale:
        col_ev, col_rad = st.columns([2, 1])
        with col_ev:
            if st.button("🔔 Genera Nuova Chiamata NUE 112", type="primary"):
                riproduci_suono_allarme()
                st.session_state.evento_corrente = {"via": "Via Roma 10", "comune": "Bergamo", "lat": 45.69, "lon": 9.66, "sintomi": "Sospetto Infarto"}
            
            if st.session_state.evento_corrente:
                ev = st.session_state.evento_corrente
                st.warning(f"📍 TARGET: {ev['via']}, {ev['comune']} \n\n 🗣️ Sintomi: {ev['sintomi']}")
                mezzi_liberi = [m for m, d in st.session_state.database_mezzi.items() if d["stato"] == "Libero in Sede"]
                m_scelto = st.multiselect("Invia Mezzi:", mezzi_liberi)
                if st.button("🚀 INVIA"):
                    for m in m_scelto:
                        st.session_state.missioni[m] = {"target": ev["via"], "timestamp_creazione": time.time()}
                        st.session_state.database_mezzi[m]["stato"] = "1 - Partenza"; st.session_state.database_mezzi[m]["colore"] = "🟡"
                    st.session_state.evento_corrente = None
                    st.success("Mezzi partiti!")

        with col_rad:
            st.subheader("📻 Registro Radio")
            st.text_area("Log Comunicazioni", "\n".join(st.session_state.registro_radio), height=300)

    with tab_mappa:
        punti = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
        st.map(pd.DataFrame(punti))

    with tab_ospedali:
        for osp, dati in st.session_state.database_ospedali.items():
            st.write(f"**{osp}**")
            st.progress(dati["pazienti"]/dati["max"])def cambio_pw_screen():
    st.title("🛡️ Sicurezza: Cambio Password Obbligatorio")
    st.warning("È il tuo primo accesso. Scegli una password diversa dal tuo nome.")
    with st.form("reset"):
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Nuova Password", type="password")
        if st.form_submit_button("AGGIORNA E ENTRA"):
            nome_base = st.session_state.utente_connesso.split(".")[0]
            if n_p == nome_base:
                st.error("La password non può essere uguale al tuo nome!")
            elif n_p == c_p and len(n_p) >= 4:
                st.session_state.utenti_db[st.session_state.utente_connesso]["pw"] = n_p
                st.session_state.utenti_db[st.session_state.utente_connesso]["cambio_obbligatorio"] = False
                st.session_state.fase_cambio_pw = False
                st.success("Password salvata!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Le password non coincidono o sono troppo brevi (min 4 car).")

# =========================================================
# 2. IL TUO CODICE ORIGINALE (INTEGRATO)
# =========================================================

# Funzioni audio originali
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

# Inizializzazione Database Mezzi e Ospedali
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }
# [Aggiungi qui gli altri mezzi se vuoi, ho accorciato per brevità]

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False}
    }

# Altre variabili di sessione originali
if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'log_chiamate' not in st.session_state: st.session_state.log_chiamate = []
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False
if 'suono_riprodotto' not in st.session_state: st.session_state.suono_riprodotto = False
if 'richiesta_chiusura' not in st.session_state: st.session_state.richiesta_chiusura = False

# Funzioni logiche originali (Distanza, Radio, ecc.)
def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    distanza = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    velocita = 220.0 if is_eli else 45.0
    return round(distanza, 1), max(1, round((distanza / velocita) * 60))

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# =========================================================
# 3. INTERFACCIA OPERATIVA (IL CUORE)
# =========================================================

def interfaccia_principale():
    # Sidebar con Logout e Impostazioni Admin
    st.sidebar.title(f"👤 {st.session_state.utente_connesso}")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.utente_connesso = None
        st.rerun()

    if st.session_state.utente_connesso == "admin":
        with st.sidebar.expander("⚙️ Gestione Utenze"):
            n = st.text_input("Nome")
            c = st.text_input("Cognome")
            if st.button("Crea Utente"):
                user = f"{n.lower()}.{c.lower()}"
                st.session_state.utenti_db[user] = {"pw": n.lower(), "ruolo": "operatore", "cambio_obbligatorio": True}
                st.success(f"Creato: {user}")

    st.sidebar.divider()

    # --- LOGICA DEL TURNO E SCRIVANIA ---
    if st.session_state.scrivania_selezionata is None:
        st.subheader("🖥️ Selezione Postazione")
        if st.button("🖥️ Scrivania 1"): st.session_state.scrivania_selezionata = 1; st.session_state.ruolo = "centrale"; st.rerun()
        if st.button("🚑 Accesso Mezzi"): st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()
    
    elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
        st.info(f"📍 Scrivania {st.session_state.scrivania_selezionata} pronta.")
        if st.button("🟢 INIZIA TURNO", use_container_width=True, type="primary"):
            st.session_state.turno_iniziato = True; st.rerun()
    
    else:
        # QUI VA TUTTO IL RESTO DEL TUO CODICE (Mappe, Chiamate, ecc.)
        # Per brevità, mostriamo un'anteprima operativa
        st.title(f"📟 SOREU Alpina - In Servizio")
        
        col_radio, col_mappa = st.columns([1, 2])
        with col_radio:
            st.subheader("📻 Registro Radio")
            st.text_area("Live Radio", "\n".join(st.session_state.registro_radio), height=300)
            if st.button("Simula Allarme Chiamata"):
                riproduci_suono_allarme()
                st.toast("🚨 NUOVA CHIAMATA!")

        with col_mappa:
            st.subheader("🗺️ Mappa Mezzi")
            punti = [{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]
            st.map(pd.DataFrame(punti))

# =========================================================
# 4. CONTROLLO FLUSSO FINALE
# =========================================================
if st.session_state.utente_connesso is None:
    login_screen()
elif st.session_state.fase_cambio_pw:
    cambio_pw_screen()
else:
    interfaccia_principale()
