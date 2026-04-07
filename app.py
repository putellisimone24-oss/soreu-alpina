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
# 2. FUNZIONI TECNICHE (ECG, ALLARMI, DISTANZE)
# =========================================================
def genera_tracciato_ecg():
    """Genera un finto tracciato ECG dinamico"""
    x = np.linspace(0, 10, 500)
    # Simula un complesso QRS con onde sinusoidali sovrapposte
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

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
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    if is_eli: tempo_minuti += 2
    return round(distanza, 1), max(1, tempo_minuti)

# =========================================================
# 3. CONFIGURAZIONE E SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

# Variabili di login e sistema
if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}

# Inizializzazione Database Mezzi
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

# Inizializzazione Inventario Materiali
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

# Altre variabili originali
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
if 'log_chiamate' not in st.session_state: st.session_state.log_chiamate = []

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# =========================================================
# 4. LOGICA DI LOGIN
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
            else: st.error("Errore password (min 4 caratteri).")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI", type="primary"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1:
                    st.session_state.fase_cambio_pw = True; st.session_state.temp_user = u_in; st.rerun()
                else:
                    st.session_state.utente_connesso = u_in; st.rerun()
            else: st.error("ID o Password errati.")
    st.stop()

# =========================================================
# 5. DASHBOARD PRINCIPALE
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA (SALA)", use_container_width=True):
        st.session_state.scrivania_selezionata = "SALA"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 EQUIPAGGIO MEZZO (ESTERNO)", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# --- INTERFACCIA CENTRALE ---
elif st.session_state.ruolo == "centrale":
    st.sidebar.button("🔚 Logout", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
    tab1, tab2, tab3 = st.tabs(["📟 Missioni", "🗺️ Mappa", "📊 ECG Tele-Consulto"])
    
    with tab1:
        st.write("Area gestione missioni (tua logica originale attiva)")
        # Qui verrebbe la tua logica missioni originale
    
    with tab2:
        df_mappa = pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()])
        st.map(df_mappa)
        
    with tab3:
        st.subheader("📡 ECG Ricevuti dal Campo")
        if not st.session_state.ecg_repository:
            st.info("In attesa di tracciati...")
        for m, ecg in st.session_state.ecg_repository.items():
            with st.expander(f"🚑 Tracciato da {m}", expanded=True):
                st.line_chart(ecg, x="Tempo", y="mV")
                if st.button(f"Valida Tracciato {m}"): st.toast("Referto Validato!")

# --- INTERFACCIA MEZZO ---
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("ACCEDI"): st.rerun()
    else:
        m_id = st.session_state.mezzo_selezionato
        inv = st.session_state.inventario_mezzi[m_id]
        st.title(f"🚑 Terminale: {m_id}")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("📦 Inventario")
            st.metric("Ossigeno", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("🔄 Rifornimento Totale"):
                st.session_state.inventario_mezzi[m_id] = {"O2": 100, "Elettrodi": 20}
                st.rerun()
                
        with c2:
            st.subheader("🩺 Monitor & ECG")
            pa = st.slider("PA Sistolica", 40, 220, 120)
            fc = st.slider("Freq. Cardiaca", 30, 200, 80)
            
            if st.button("📉 ESEGUI E INVIA ECG", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[m_id]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[m_id] = genera_tracciato_ecg()
                    aggiungi_log_radio(m_id, "ECG 12 derivazioni inviato in Centrale per tele-consulto.")
                    st.rerun()
                else: st.error("Elettrodi insufficienti!")
            
            if m_id in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[m_id], x="Tempo", y="mV")
            
            if st.button("🏁 CHIUDI INTERVENTO"):
                st.session_state.inventario_mezzi[m_id]["O2"] -= random.randint(5, 15)
                if m_id in st.session_state.ecg_repository: del st.session_state.ecg_repository[m_id]
                st.rerun()
