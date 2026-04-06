import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. SISTEMA DI SICUREZZA E UTENTI (NOVITÀ)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore PRO", layout="wide")

# Database utenti persistente nella sessione
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin", "ruolo": "admin", "cambio_obbligatorio": False},
        "mario.rossi": {"pw": "mario", "ruolo": "operatore", "cambio_obbligatorio": True}
    }

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

def login_screen():
    st.title("🔐 SOREU Alpina - Accesso Riservato")
    with st.container(border=True):
        u = st.text_input("Username (nome.cognome)").lower()
        p = st.text_input("Password", type="password")
        if st.button("ACCEDI", use_container_width=True, type="primary"):
            if u in st.session_state.utenti_db and st.session_state.utenti_db[u]["pw"] == p:
                st.session_state.utente_connesso = u
                if st.session_state.utenti_db[u]["cambio_obbligatorio"]:
                    st.session_state.fase_cambio_pw = True
                st.rerun()
            else:
                st.error("Credenziali non valide.")

def cambio_pw_screen():
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
