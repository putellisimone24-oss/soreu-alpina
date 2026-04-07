import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE) - POTENZIATO
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db', check_same_thread=False)
    c = conn.cursor()
    # Tabella Utenti
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    
    # Tabella Missioni (Condivisa tra tutti i PC)
    c.execute('''CREATE TABLE IF NOT EXISTS missioni_attive 
                 (mezzo TEXT PRIMARY KEY, target TEXT, codice TEXT, ospedale TEXT, 
                  stato_clinico_ok INTEGER DEFAULT 0, ossigeno INTEGER DEFAULT 100)''')
    
    # Tabella Statistiche (Per il fine turno)
    c.execute('''CREATE TABLE IF NOT EXISTS statistiche 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, codice TEXT, ospedale TEXT, tempo_intervento INTEGER)''')

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

# Funzioni di supporto Database
def salva_missione_db(mezzo, target, codice, ospedale):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO missioni_attive (mezzo, target, codice, ospedale, stato_clinico_ok) VALUES (?,?,?,?,0)", 
              (mezzo, target, codice, ospedale))
    conn.commit()
    conn.close()

def get_missioni_db():
    conn = sqlite3.connect('centrale.db')
    df = pd.read_sql_query("SELECT * FROM missioni_attive", conn)
    conn.close()
    return df

def aggiorna_clinica_db(mezzo, pronto):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    val = 1 if pronto else 0
    c.execute("UPDATE missioni_attive SET stato_clinico_ok=? WHERE mezzo=?", (val, mezzo))
    conn.commit()
    conn.close()

def elimina_missione_db(mezzo):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("DELETE FROM missioni_attive WHERE mezzo=?", (mezzo,))
    conn.commit()
    conn.close()

init_db()

# =========================================================
# 2. LOGICA ORIGINALE E NUOVE AGGIUNTE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Real-Time", layout="wide")

# (Mantieni le tue funzioni audio e calcolo distanza qui...)
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False

# --- GESTIONE LOGIN (come nel tuo file) ---
if st.session_state.utente_connesso is None:
    # ... (Codice login invariato) ...
    st.title("🔐 SOREU Alpina - Login")
    u_in = st.text_input("Username").lower().strip()
    p_in = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        st.session_state.utente_connesso = u_in
        st.rerun()
    st.stop()

# --- INIZIALIZZAZIONE VARIABILI SESSIONE ---
if 'mezzi_fuori_servizio' not in st.session_state: st.session_state.mezzi_fuori_servizio = set()
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "tipo": "MSA", "lat": 45.6869, "lon": 9.6272, "sede": "Papa Giovanni"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "tipo": "MSB", "lat": 45.6928, "lon": 9.6428, "sede": "CRI Bergamo"},
        # Aggiungi gli altri mezzi qui...
    }
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6}
    }

# ==================== INTERFACCIA CENTRALE ====================
if st.session_state.get('ruolo') == "centrale":
    st.title("🎧 Centrale Operativa SOREU")
    
    tab1, tab2, tab3 = st.tabs(["Inviante", "Stato Mezzi", "Statistiche Turno"])
    
    with tab1:
        # LOGICA INVIO MEZZI (Update per DB)
        # Quando premi "INVIA MEZZI", usa:
        # salva_missione_db(m_scelto, target, codice, ospedale)
        st.write("Ricezione chiamate e gestione real-time...")
        df_attive = get_mission_db()
        st.table(df_attive)

    with tab3:
        st.header("📊 Dashboard Statistiche")
        conn = sqlite3.connect('centrale.db')
        df_stats = pd.read_sql_query("SELECT * FROM statistiche", conn)
        conn.close()
        if not df_stats.empty:
            st.bar_chart(df_stats['codice'].value_counts())
            st.metric("Missioni Totali", len(df_stats))

# ==================== INTERFACCIA MEZZO (NUOVA) ====================
elif st.session_state.get('ruolo') == "mezzo":
    mio_mezzo = st.selectbox("Seleziona il tuo Mezzo", list(st.session_state.database_mezzi.keys()))
    
    # Controllo se il mezzo è scarico (CONSUMABILI)
    if mio_mezzo in st.session_state.mezzi_fuori_servizio:
        st.error(f"⚠️ {mio_mezzo} deve essere rifornito!")
        if st.button("🔄 ESEGUI RIFORNIMENTO (10 sec)"):
            with st.spinner("Caricamento presidi e ossigeno..."):
                time.sleep(5)
            st.session_state.mezzi_fuori_servizio.remove(mio_mezzo)
            st.rerun()
        st.stop()

    # Leggi missione dal DB (Multi-user)
    df_m = get_missioni_db()
    missione = df_m[df_m['mezzo'] == mio_mezzo]

    if not missione.empty:
        st.success(f"🔴 MISSIONE ATTIVA: {missione.iloc[0]['target']}")
        
        # SCHEDA CLINICA DETTAGLIATA (CHECK-LIST)
        st.subheader("📋 Check-list Clinica Obbligatoria")
        c1 = st.checkbox("Paziente Immobilizzato")
        c2 = st.checkbox("Parametri Rilevati")
        c3 = st.checkbox("Accesso Venoso (se MSA) / Presidi pronti")
        
        tutto_pronto = c1 and c2 and c3
        aggiorna_clinica_db(mio_mezzo, tutto_pronto)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📍 Arrivo sul Posto"):
                st.toast("Arrivo comunicato")
        with col2:
            # BLOCCO STATO 3
            if not tutto_pronto:
                st.warning("Completa la check-list per partire verso l'ospedale.")
            if st.button("🏥 Partenza Ospedale (STATO 3)", disabled=not tutto_pronto):
                st.info("In viaggio...")

        if st.button("🏁 Fine Missione (STATO 4)"):
            # Aggiorna statistiche
            conn = sqlite3.connect('centrale.db')
            conn.execute("INSERT INTO statistiche (codice, ospedale) VALUES (?,?)", 
                         (missione.iloc[0]['codice'], missione.iloc[0]['ospedale']))
            conn.commit()
            conn.close()
            
            elimina_missione_db(mio_mezzo)
            st.session_state.mezzi_fuori_servizio.add(mio_mezzo) # Forza rifornimento
            st.rerun()
    else:
        st.info("In attesa di missioni dalla centrale...")

# Pulsante per simulare il cambio ruolo durante i test
if st.sidebar.button("Cambia Interfaccia (Centrale/Mezzo)"):
    st.session_state.ruolo = "mezzo" if st.session_state.get('ruolo') == "centrale" else "centrale"
    st.rerun()
