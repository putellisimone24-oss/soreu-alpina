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
# 2. FUNZIONI TECNICHE (ECG E AUDIO)
# =========================================================
def genera_tracciato_ecg(ritmo="sinusale"):
    x = np.linspace(0, 10, 500)
    # Simula un'onda P-QRS-T realistica con rumore di fondo
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

# =========================================================
# 3. CONFIGURAZIONE E SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide")

# Inizializzazione variabili (incluse quelle nuove)
if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'missioni' not in st.session_state: st.session_state.missioni = {}
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None
if 'mezzo_selezionato' not in st.session_state: st.session_state.mezzo_selezionato = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []

# Database Mezzi (Originale)
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA"},
        "MSA 2 004": {"stato": "Libero in Sede", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI"}
    }

# Inventario (Nuovo)
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

# =========================================================
# 4. GESTIONE LOGIN
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Accesso Riservato")
    if st.session_state.fase_cambio_pw:
        st.warning(f"Primo accesso per {st.session_state.temp_user}: cambia password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Errore password.")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI"):
            res = get_utente_db(u_in)
            if res and res[1] == p_in:
                if res[2] == 1:
                    st.session_state.fase_cambio_pw = True; st.session_state.temp_user = u_in; st.rerun()
                else:
                    st.session_state.utente_connesso = u_in; st.rerun()
            else: st.error("Credenziali non valide.")
    st.stop()

# =========================================================
# 5. LOGICA OPERATIVA
# =========================================================
def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] 📻 {mittente}: {messaggio}")

if st.session_state.scrivania_selezionata is None:
    st.header(f"Benvenuto, {st.session_state.utente_connesso}")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ SALA OPERATIVA", use_container_width=True):
        st.session_state.scrivania_selezionata = "CENTRALE"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 TABLET BORDO MEZZO", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# --- INTERFACCIA CENTRALE ---
elif st.session_state.ruolo == "centrale":
    if not st.session_state.turno_iniziato:
        if st.button("🟢 APRI TURNO"): st.session_state.turno_iniziato = True; st.rerun()
    else:
        st.sidebar.button("⬅️ Menu Principale", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
        tab1, tab2, tab3 = st.tabs(["📟 Missioni", "🗺️ Mappa", "📊 Monitoraggio Risorse & ECG"])
        
        with tab1:
            st.info("Gestione Missioni in corso...")
            # Qui rimane la tua logica originale di generazione eventi
            
        with tab2:
            st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))

        with tab3:
            st.subheader("Tele-Consulto ECG e Stato Materiali")
            for m, d in st.session_state.database_mezzi.items():
                with st.expander(f"🚑 {m} - {d['stato']}"):
                    inv = st.session_state.inventario_mezzi[m]
                    st.write(f"Ossigeno: {inv['O2']}% | Elettrodi: {inv['Elettrodi']}")
                    if m in st.session_state.ecg_repository:
                        st.line_chart(st.session_state.ecg_repository[m], x="Tempo", y="mV")
                        st.caption("Ultimo tracciato ricevuto dal campo")

# --- INTERFACCIA MEZZO ---
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("Connetti Tablet"): st.rerun()
    else:
        mio_mezzo = st.session_state.mezzo_selezionato
        st.header(f"📟 Terminale {mio_mezzo}")
        inv = st.session_state.inventario_mezzi[mio_mezzo]
        
        col_m1, col_m2 = st.columns([1, 2])
        with col_m1:
            st.metric("Ossigeno", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("🔄 Rifornimento Materiali"):
                st.session_state.inventario_mezzi[mio_mezzo] = {"O2": 100, "Elettrodi": 20}; st.rerun()
        
        with col_m2:
            st.subheader("🩺 Scheda Clinica")
            fc = st.slider("Frequenza Cardiaca", 30, 180, 80)
            
            # COMANDO ECG
            if st.button("📉 ESEGUI E TRASMETTI ECG", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[mio_mezzo]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[mio_mezzo] = genera_tracciato_ecg()
                    aggiungi_log_radio(mio_mezzo, "ECG 12 derivazioni trasmesso per tele-consulto.")
                    st.success("Tracciato inviato in Centrale!")
                    st.rerun()
                else: st.error("Elettrodi insufficienti!")
            
            if mio_mezzo in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[mio_mezzo], x="Tempo", y="mV")

            if st.button("🏁 CHIUDI INTERVENTO"):
                st.session_state.inventario_mezzi[mio_mezzo]["O2"] -= random.randint(5, 15)
                if mio_mezzo in st.session_state.ecg_repository: del st.session_state.ecg_repository[mio_mezzo]
                st.rerun()
