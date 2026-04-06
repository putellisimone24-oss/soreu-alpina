import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. CORE: DATABASE SQLITE PER UTENTI PERSISTENTI
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
# 2. SICUREZZA E SESSIONE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Sistema Integrato", layout="wide")

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

if st.session_state.utente_connesso is None:
    st.title("🚑 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}. Scegli una nuova password.")
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
        if st.button("LOG IN", type="primary"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("Accesso Negato.")
    st.stop()

# =========================================================
# 3. LOGICA OPERATIVA E DATABASE MEZZI/OSPEDALI
# =========================================================

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo)

if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CBBG_014.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6725, "lon": 9.6450, "tipo": "MSB", "sede": "Croce Bianca Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Bergamo"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4}
    }

for k in ['missioni', 'registro_radio', 'evento_corrente', 'time_mult', 'auto_mode', 'scrivania_selezionata', 'turno_iniziato']:
    if k not in st.session_state:
        if k == 'missioni': st.session_state[k] = {}
        elif k == 'registro_radio': st.session_state[k] = []
        elif k == 'time_mult': st.session_state[k] = 1.0
        elif k == 'auto_mode': st.session_state[k] = False
        else: st.session_state[k] = None

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] 📻 {mittente}: {messaggio}")

# Automazione Stati
def aggiorna_automazione():
    now = time.time()
    rimuovere = []
    for m, miss in st.session_state.missioni.items():
        passato = now - miss["timestamp_creazione"]
        mult = st.session_state.time_mult
        db = st.session_state.database_mezzi
        if passato < 30/mult: 
            db[m]["stato"] = "1 - Partenza"; db[m]["colore"] = "🟡"
        elif passato < 60/mult: 
            db[m]["stato"] = "2 - Sul Posto"; db[m]["colore"] = "🔴"
        elif passato >= 180/mult:
            db[m]["stato"], db[m]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m, "Mezzo Libero.")
            rimuovere.append(m)
    for r in rimuovere: del st.session_state.missioni[r]

if st.session_state.auto_mode: aggiorna_automazione()

# =========================================================
# 4. INTERFACCIA E SIDEBAR
# =========================================================
with st.sidebar:
    st.header(f"Operatore: {st.session_state.utente_connesso}")
    if st.button("🚪 Esci"):
        st.session_state.utente_connesso = None
        st.rerun()
    st.divider()
    if st.session_state.utente_connesso == 'admin':
        with st.expander("🛠️ Admin: Aggiungi Utente"):
            u_nuovo = st.text_input("User ID")
            p_nuovo = st.text_input("Password Iniziale", type="password")
            if st.button("SALVA NEL DB"):
                if aggiungi_nuovo_utente_db(u_nuovo, p_nuovo): st.success("Creato!")
                else: st.error("Errore (esiste già?)")
    st.divider()
    st.session_state.auto_mode = st.toggle("🤖 Automazione Equipaggi")
    vel = st.radio("Velocità", ["Normale", "2X", "5X"])
    st.session_state.time_mult = 1.0 if vel=="Normale" else (2.0 if vel=="2X" else 5.0)

# Main Logic
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Seleziona Postazione Operativa")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA (SOREU)"): st.session_state.scrivania_selezionata = "CENTRAL"; st.rerun()
    if c2.button("🚑 EQUIPAGGIO MEZZO"): st.session_state.scrivania_selezionata = "MEZZO"; st.rerun()

elif st.session_state.scrivania_selezionata == "CENTRAL":
    if not st.session_state.turno_iniziato:
        if st.button("🟢 INIZIA TURNO"): st.session_state.turno_iniziato = True; st.rerun()
    else:
        t1, t2, t3 = st.tabs(["📝 Chiamate", "🚑 Mezzi", "🏥 Ospedali"])
        with t1:
            if st.button("🔔 Genera Emergenza"):
                st.session_state.evento_corrente = {"via": "Piazza Vecchia, Bergamo", "lat": 45.7042, "lon": 9.6622, "codice": "ROSSO"}
            if st.session_state.evento_corrente:
                st.error(f"EMERGENZA: {st.session_state.evento_corrente['via']}")
                scelti = st.multiselect("Invia:", [m for m, d in st.session_state.database_mezzi.items() if d["stato"]=="Libero in Sede"])
                if st.button("DISPACHING"):
                    for s in scelti:
                        st.session_state.missioni[s] = {"timestamp_creazione": time.time()}
                        st.session_state.database_mezzi[s]["stato"] = "1 - Partenza"
                    st.session_state.evento_corrente = None; st.rerun()
        with t2:
            st.dataframe(pd.DataFrame.from_dict(st.session_state.database_mezzi, orient='index'))
        with t3:
            st.write(st.session_state.database_ospedali)
            st.text_area("Log Radio", "\n".join(st.session_state.registro_radio), height=200)

else:
    mio_m = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
    st.header(f"📟 Terminale Bordo: {mio_m}")
    st.write(f"Stato: **{st.session_state.database_mezzi[mio_m]['stato']}**")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🚨 1"): st.session_state.database_mezzi[mio_m]["stato"] = "1 - Partenza"; aggiungi_log_radio(mio_m, "Stato 1"); st.rerun()
    if c2.button("📍 2"): st.session_state.database_mezzi[mio_m]["stato"] = "2 - Sul Posto"; aggiungi_log_radio(mio_m, "Stato 2"); st.rerun()
    if c3.button("🏥 3"): st.session_state.database_mezzi[mio_m]["stato"] = "3 - Trasporto"; aggiungi_log_radio(mio_m, "Stato 3"); st.rerun()
    if c4.button("🟢 4"): 
        st.session_state.database_mezzi[mio_m]["stato"] = "Libero in Sede"
        if mio_m in st.session_state.missioni: del st.session_state.missioni[mio_m]
        aggiungi_log_radio(mio_m, "Stato 4 - Libero"); st.rerun()
