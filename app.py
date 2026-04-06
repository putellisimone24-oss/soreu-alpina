import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE)
# =========================================================
def init_db():
    """Inizializza il database utenti se non esiste."""
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    
    # Controllo se il database è vuoto per inserire i primi utenti
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [
            ('admin', 'admin', 0, 'Admin'),
            ('simone.putelli', 'simone', 1, 'Operatore'),
            ('simone.marinoni', 'simone', 1, 'Operatore'),
            ('operatore.test', '118', 1, 'Operatore')
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
    except:
        return False

# Esecuzione inizializzazione all'avvio dello script
init_db()

# =========================================================
# 2. LOGICA DI SICUREZZA E LOGIN
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# Schermata di Accesso
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login Sistema")
    
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}: Cambia la password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Le password non coincidono o sono troppo brevi (min 4 car).")
    else:
        u_in = st.text_input("ID Utente").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI", type="primary"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1: # Cambio obbligatorio
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("Credenziali errate.")
    st.stop()

# =========================================================
# 3. DATABASE MEZZI, OSPEDALI E FUNZIONI TECNICHE
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo_minuti)

if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Bergamo"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6}
    }

# Variabili di stato missione
for key in ['missioni', 'registro_radio', 'notifiche_centrale', 'log_chiamate']:
    if key not in st.session_state: st.session_state[key] = [] if key != 'missioni' else {}

if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False

# =========================================================
# 4. SIDEBAR (LOGOUT + ADMIN PERMANENTE)
# =========================================================
with st.sidebar:
    st.title(f"👤 {st.session_state.utente_connesso.upper()}")
    if st.button("🚪 LOGOUT", use_container_width=True):
        st.session_state.utente_connesso = None
        st.rerun()
    
    st.divider()
    
    # GESTIONE UTENTI (Solo Admin - Scrive su centrale.db)
    if st.session_state.utente_connesso == 'admin':
        with st.expander("🛠️ GESTIONE UTENTI (DATABASE)"):
            new_u = st.text_input("Nuovo ID Utente").lower().strip()
            new_p = st.text_input("Password Temporanea", type="password")
            if st.button("SALVA NEL SERVER"):
                if new_u and new_p:
                    if aggiungi_nuovo_utente_db(new_u, new_p):
                        st.success(f"Utente {new_u} salvato permanentemente!")
                    else: st.error("Errore: Utente già esistente.")
                else: st.warning("Compila tutti i campi.")

    st.divider()
    st.session_state.auto_mode = st.toggle("🤖 Automazione Mezzi", value=st.session_state.auto_mode)
    vel = st.radio("Velocità Simulazione", ["Normale", "2X", "5X"])
    st.session_state.time_mult = 1.0 if vel=="Normale" else (2.0 if vel=="2X" else 5.0)

# =========================================================
# 5. INTERFACCIA OPERATIVA (CENTRALE / MEZZO)
# =========================================================

if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Seleziona Postazione Operativa")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA (SOREU)", use_container_width=True):
        st.session_state.scrivania_selezionata = "CENTRAL"; st.rerun()
    if c2.button("🚑 EQUIPAGGIO MEZZO", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.rerun()

elif st.session_state.scrivania_selezionata == "CENTRAL":
    if not st.session_state.turno_iniziato:
        if st.button("🟢 INIZIA TURNO SOREU", type="primary", use_container_width=True):
            st.session_state.turno_iniziato = True; st.rerun()
    else:
        tab1, tab2, tab3 = st.tabs(["🔥 EMERGENZE", "🚑 MEZZI", "🏥 OSPEDALI"])
        with tab1:
            st.write("Monitor in attesa di eventi...")
            # Qui si sviluppa la logica di invio eventi...
        with tab2:
            st.dataframe(pd.DataFrame.from_dict(st.session_state.database_mezzi, orient='index'), use_container_width=True)
        with tab3:
            st.write(st.session_state.database_ospedali)

else:
    mio_m = st.selectbox("Identifica Mezzo", list(st.session_state.database_mezzi.keys()))
    st.header(f"📟 Terminale Bordo: {mio_m}")
    st.write(f"Stato Attuale: **{st.session_state.database_mezzi[mio_m]['stato']}**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚨 STATO 1 - PARTENZA", use_container_width=True):
            st.session_state.database_mezzi[mio_m]["stato"] = "1 - Partenza"; st.rerun()
    with col2:
        if st.button("📍 STATO 2 - ARRIVO POSTO", use_container_width=True):
            st.session_state.database_mezzi[mio_m]["stato"] = "2 - Arrivo"; st.rerun()
