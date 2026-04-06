import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. CONFIGURAZIONE PAGINA E GESTIONE ACCESSI (IAM)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

# Database Utenti Persistente in sessione
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin", "cambio_obbligatorio": False, "ruolo": "Admin"},
        "mario.rossi": {"pw": "mario", "cambio_obbligatorio": True, "ruolo": "Operatore"}
    }

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# --- LOGICA DI LOGIN ---
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Accesso Riservato")
    
    if st.session_state.fase_cambio_pw:
        st.warning("🔄 Primo accesso: è necessario cambiare la password.")
        nuova_p = st.text_input("Nuova Password", type="password")
        conf_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI", type="primary"):
            if nuova_p == conf_p and len(nuova_p) > 0:
                user = st.session_state.temp_user
                st.session_state.utenti_db[user]["pw"] = nuova_p
                st.session_state.utenti_db[user]["cambio_obbligatorio"] = False
                st.session_state.utente_connesso = user
                st.session_state.fase_cambio_pw = False
                st.rerun()
            else:
                st.error("Le password non coincidono.")
    else:
        u_input = st.text_input("ID Utente (nome.cognome)").lower()
        p_input = st.text_input("Password", type="password")
        if st.button("ACCEDI AL SISTEMA", type="primary"):
            if u_input in st.session_state.utenti_db and st.session_state.utenti_db[u_input]["pw"] == p_input:
                if st.session_state.utenti_db[u_input]["cambio_obbligatorio"]:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_input
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_input
                    st.rerun()
            else:
                st.error("Credenziali non corrette.")
    st.stop()

# =========================================================
# 2. FUNZIONI TECNICHE (AUDIO, CALCOLO, LOG)
# =========================================================
def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay><source src="{audio_url}"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay><source src="{audio_url}"></audio>', height=0)

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

# =========================================================
# 3. DATABASE E VARIABILI DI SESSIONE
# =========================================================
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6}
    }

database_mail = [
    {"mittente": "Milano Sport", "oggetto": "Maratona", "testo": "Richiesta copertura.", "lat": 45.69, "lon": 9.66, "tipo": "SPORT"}
]

for key in ['missioni', 'notifiche_centrale', 'registro_radio', 'log_chiamate']:
    if key not in st.session_state: st.session_state[key] = [] if 'notifiche' in key or 'registro' in key or 'log' in key else {}

if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False

# =========================================================
# 4. DASHBOARD ADMIN E BARRA LATERALE
# =========================================================
with st.sidebar:
    st.title(f"👤 {st.session_state.utente_connesso}")
    if st.button("🚪 LOGOUT SISTEMA"):
        st.session_state.utente_connesso = None
        st.rerun()
    
    if st.session_state.utente_connesso == "admin":
        st.divider()
        st.subheader("🛠️ Gestione Utenze")
        new_u = st.text_input("Nuovo ID")
        new_p = st.text_input("PW Iniziale")
        if st.button("Aggiungi Operatore"):
            if new_u and new_p:
                st.session_state.utenti_db[new_u] = {"pw": new_p, "cambio_obbligatorio": True, "ruolo": "Operatore"}
                st.success(f"Creato: {new_u}")
        
        st.write("Elenco Utenti:")
        for usr in list(st.session_state.utenti_db.keys()):
            if usr != "admin":
                if st.button(f"Elimina {usr}", key=f"del_{usr}"):
                    del st.session_state.utenti_db[usr]
                    st.rerun()

# =========================================================
# 5. LOGICA OPERATIVA (CENTRALE / MEZZO)
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione Operativa")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🖥️ Scrivania 1", use_container_width=True): st.session_state.scrivania_selezionata = 1; st.rerun()
    with c3:
        if st.button("🚑 Mezzo Esterno", use_container_width=True): st.session_state.scrivania_selezionata = "MEZZO"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.scrivania_selezionata != "MEZZO":
    st.info(f"Postazione {st.session_state.scrivania_selezionata} pronta.")
    if st.button("🔴 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

else:
    # --- INTERFACCIA CENTRALE ---
    if st.session_state.scrivania_selezionata != "MEZZO":
        tab_invio, tab_mappa, tab_ps = st.tabs(["📟 Missioni", "🗺️ Mappa", "🏥 Ospedali"])
        
        with tab_invio:
            col_ev, col_rad = st.columns([2, 1])
            with col_ev:
                if st.button("🔔 Genera Emergenza", type="primary"):
                    riproduci_suono_allarme()
                    st.session_state.evento_corrente = {"via": "Piazza Vecchia", "comune": "Bergamo", "lat": 45.70, "lon": 9.66, "sintomi": "Sospetto IMA"}
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.warning(f"📍 TARGET: {ev['via']}\n\n🩺 Sintomi: {ev['sintomi']}")
                    mezzi_liberi = [m for m, d in st.session_state.database_mezzi.items() if d["stato"] == "Libero in Sede"]
                    m_scelti = st.multiselect("Assegna Mezzi:", mezzi_liberi)
                    if st.button("🚀 INVIA"):
                        for m in m_scelti:
                            st.session_state.missioni[m] = {"target": ev["via"], "timestamp_creazione": time.time(), "ospedale": "Osp. Papa Giovanni XXIII"}
                            st.session_state.database_mezzi[m]["stato"] = "1 - Partenza"; st.session_state.database_mezzi[m]["colore"] = "🟡"
                            aggiungi_log_radio(m, "STATO 1: In missione.")
                        st.session_state.evento_corrente = None; st.rerun()
            with col_rad:
                st.text_area("Radio Log", "\n".join(st.session_state.registro_radio), height=300)

        with tab_mappa:
            st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))

    # --- INTERFACCIA MEZZO ---
    else:
        if 'mio_mezzo' not in st.session_state:
            st.session_state.mio_mezzo = st.selectbox("Seleziona Mezzo:", list(st.session_state.database_mezzi.keys()))
            if st.button("Login Mezzo"): st.rerun()
        else:
            mio = st.session_state.mio_mezzo
            dati = st.session_state.database_mezzi[mio]
            st.header(f"🚑 Terminale: {mio}")
            st.write(f"Stato: {dati['stato']}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📍 Arrivo Posto"): 
                    dati["stato"] = "2 - Sul Posto"; aggiungi_log_radio(mio, "Arrivati."); st.rerun()
                if st.button("🏁 Libero"): 
                    dati["stato"] = "Libero in Sede"; dati["colore"] = "🟢"
                    if mio in st.session_state.missioni: del st.session_state.missioni[mio]
                    st.rerun()
            with c2:
                st.subheader("🩺 Clinica")
                pa = st.slider("PA Sistolica", 50, 200, 120)
                fc = st.slider("FC", 30, 150, 80)
                if st.button("📑 Trasmetti Parametri"):
                    st.session_state.notifiche_centrale.append(f"{mio}: PA {pa}, FC {fc}")
                    aggiungi_log_radio(mio, f"Parametri: PA {pa}, FC {fc}")
                    st.success("Trasmessi!")
