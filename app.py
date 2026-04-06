import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. SISTEMA DI ACCESSO E GESTIONE UTENZE (IAM)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

# Database Utenti in sessione
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin", "cambio_obbligatorio": False, "ruolo": "Admin"},
        "operatore.test": {"pw": "test", "cambio_obbligatorio": True, "ruolo": "Operatore"}
    }

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# Schermata di Login / Cambio PW
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login Sistema")
    
    if st.session_state.fase_cambio_pw:
        st.warning("⚠️ Primo accesso: Cambia la tua password per continuare.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) > 0:
                u = st.session_state.temp_user
                st.session_state.utenti_db[u]["pw"] = n_p
                st.session_state.utenti_db[u]["cambio_obbligatorio"] = False
                st.session_state.utente_connesso = u
                st.rerun()
            else:
                st.error("Le password non coincidono.")
    else:
        u_in = st.text_input("ID Utente (nome.cognome)").lower()
        p_in = st.text_input("Password", type="password")
        if st.button("LOG IN", type="primary"):
            if u_in in st.session_state.utenti_db and st.session_state.utenti_db[u_in]["pw"] == p_in:
                if st.session_state.utenti_db[u_in]["cambio_obbligatorio"]:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else:
                st.error("Credenziali non valide.")
    st.stop()

# =========================================================
# 2. IL TUO SIMULATORE ORIGINALE (INTEGRALE)
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

# DATABASE MEZZI
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

# DATABASE OSPEDALI
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

# INIZIALIZZAZIONE VARIABILI
for key in ['missioni', 'notifiche_centrale', 'registro_radio', 'log_chiamate']:
    if key not in st.session_state: st.session_state[key] = [] if 'notifiche' in key or 'registro' in key or 'log' in key else {}

if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0
if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False
if 'suono_riprodotto' not in st.session_state: st.session_state.suono_riprodotto = False

# FUNZIONI LOGICHE
def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    if is_eli: tempo_minuti += 2
    return round(distanza, 1), max(1, tempo_minuti)

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# GESTIONE AUTOMATICA STATI
def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        mult = st.session_state.time_mult
        t_trascorso = now - creazione
        
        if t_trascorso < 30/mult:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, "STATO 1: Partenza sede.")
        elif t_trascorso < 60/mult:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Arrivati sul posto.")
        elif t_trascorso >= 60/mult and t_trascorso < 120/mult:
            if not miss.get("richiesto_ospedale", False):
                st.session_state.notifiche_centrale.append(f"🩺 {m_nome} richiede ospedale!")
                aggiungi_log_radio(m_nome, "Valutazione completata. Richiediamo destinazione.")
                riproduci_suono_notifica()
                st.session_state.missioni[m_nome]["richiesto_ospedale"] = True
        elif t_trascorso >= 120/mult and t_trascorso < 180/mult:
            if db[m_nome]["stato"] != "3 - Partenza per ospedale":
                db[m_nome]["stato"] = "3 - Partenza per ospedale"
                aggiungi_log_radio(m_nome, "STATO 3: Carico paziente, direzione ospedale.")
        elif t_trascorso >= 240/mult:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, "STATO 4: Fine intervento. Mezzo LIBERO.")
            dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
            if dest in st.session_state.database_ospedali:
                st.session_state.database_ospedali[dest]["pazienti"] += 1
            voci_da_rimuovere.append(m_nome)
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.missioni and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

# --- BARRA LATERALE E ADMIN ---
with st.sidebar:
    st.header(f"👤 {st.session_state.utente_connesso}")
    if st.button("🚪 LOGOUT SISTEMA"):
        st.session_state.utente_connesso = None
        st.rerun()

    # Pannello Admin
    if st.session_state.utente_connesso == "admin":
        st.divider()
        st.subheader("🛠️ Gestione Utenze")
        nuovo_id = st.text_input("Nuovo ID (nome.cognome)")
        nuova_pw = st.text_input("Password Iniziale")
        if st.button("AGGIUNGI UTENTE"):
            if nuovo_id and nuova_pw:
                st.session_state.utenti_db[nuovo_id] = {"pw": nuova_pw, "cambio_obbligatorio": True, "ruolo": "Operatore"}
                st.success(f"Utente {nuovo_id} creato.")
        
        st.write("Utenti Attivi:")
        for usr in list(st.session_state.utenti_db.keys()):
            if usr != "admin":
                if st.button(f"Elimina {usr}", key=f"del_{usr}"):
                    del st.session_state.utenti_db[usr]
                    st.rerun()

    st.divider()
    if st.session_state.scrivania_selezionata:
        if st.button("⬅️ Cambia Ruolo"):
            st.session_state.scrivania_selezionata = None; st.rerun()

# --- INTERFACCIA OPERATIVA (IL TUO LAYOUT) ---
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione di Lavoro")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🖥️ Scrivania 1 (Centrale)", use_container_width=True): st.session_state.scrivania_selezionata = 1; st.rerun()
    with c2:
        if st.button("🖥️ Scrivania 2 (Centrale)", use_container_width=True): st.session_state.scrivania_selezionata = 2; st.rerun()
    with c3:
        if st.button("🚑 Equipaggio Mezzo", use_container_width=True): st.session_state.scrivania_selezionata = "MEZZO"; st.rerun()

elif not st.session_state.turno_iniziato and st.session_state.scrivania_selezionata != "MEZZO":
    st.title(f"Postazione {st.session_state.scrivania_selezionata}")
    if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

else:
    # --- LOGICA CENTRALE ---
    if st.session_state.scrivania_selezionata != "MEZZO":
        tab_invio, tab_risorse, tab_ps = st.tabs(["📝 Nuove Missioni", "🚑 Stato Risorse", "🏥 Monitoraggio PS"])
        
        with tab_invio:
            col_evento, col_mappa = st.columns([1.5, 2])
            with col_evento:
                st.header("📋 Ricezione Chiamate")
                if st.button("🔔 Forza Chiamata", type="primary", use_container_width=True):
                    st.session_state.evento_corrente = {"via": "Piazza Vecchia", "comune": "Bergamo", "lat": 45.7042, "lon": 9.6622, "sintomi": "Dolore Toracico", "codice_reale": "ROSSO"}
                    riproduci_suono_allarme(); st.rerun()
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.warning(f"📍 Target: {ev['via']}, {ev['comune']}\n\n🗣️ Sintomi: {ev['sintomi']}")
                    codice = st.selectbox("Codice", ["ROSSO", "GIALLO", "VERDE"])
                    
                    mezzi_calcolo = []
                    for nome, d in st.session_state.database_mezzi.items():
                        if d["stato"] == "Libero in Sede":
                            dist, tempo = calcola_distanza_e_tempo(d["lat"], d["lon"], ev["lat"], ev["lon"], (d["tipo"]=="ELI"))
                            mezzi_calcolo.append({"Mezzo": nome, "Tempo": tempo})
                    
                    df_mezzi = pd.DataFrame(mezzi_calcolo).sort_values("Tempo")
                    st.dataframe(df_mezzi, hide_index=True)
                    
                    m_scelti = st.multiselect("Seleziona Mezzi", df_mezzi["Mezzo"].tolist())
                    if st.button("🚀 INVIA"):
                        for m in m_scelti:
                            st.session_state.missioni[m] = {"target": ev["via"], "timestamp_creazione": time.time(), "ospedale_assegnato": "Osp. Papa Giovanni XXIII"}
                            st.session_state.database_mezzi[m]["stato"] = "1 - Partenza da sede"; st.session_state.database_mezzi[m]["colore"] = "🟡"
                        st.session_state.evento_corrente = None; st.rerun()
            
            with col_mappa:
                st.header("🗺️ Mappa Area")
                st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))
                st.text_area("📻 Registro Radio", "\n".join(st.session_state.registro_radio), height=200)

        with tab_risorse:
            for m, d in st.session_state.database_mezzi.items():
                st.write(f"{d['colore']} **{m}** - {d['stato']} ({d['sede']})")

    # --- LOGICA MEZZO ---
    else:
        if 'mio_mezzo' not in st.session_state:
            st.session_state.mio_mezzo = st.selectbox("Identificati (Seleziona Mezzo):", list(st.session_state.database_mezzi.keys()))
            if st.button("Login"): st.rerun()
        else:
            mio = st.session_state.mio_mezzo
            dati = st.session_state.database_mezzi[mio]
            st.header(f"🚑 Terminale Mezzo: {mio}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Stato Operativo")
                if st.button("🚨 STATO 1 (Partenza)"): dati["stato"] = "1 - Partenza"; aggiungi_log_radio(mio, "Partiti."); st.rerun()
                if st.button("📍 STATO 2 (Arrivo Posto)"): dati["stato"] = "2 - Sul Posto"; aggiungi_log_radio(mio, "Arrivati sul posto."); st.rerun()
                if st.button("🏁 STATO 4 (Libero)"): 
                    dati["stato"] = "Libero in Sede"; dati["colore"] = "🟢"
                    if mio in st.session_state.missioni: del st.session_state.missioni[mio]
                    st.rerun()
            with c2:
                st.subheader("🩺 Scheda Paziente")
                pa = st.slider("PA Sistolica", 50, 200, 120)
                fc = st.slider("Freq. Cardiaca", 30, 180, 80)
                if st.button("📑 Trasmetti Parametri"):
                    st.session_state.notifiche_centrale.append(f"Parametri da {mio}: PA {pa}, FC {fc}")
                    aggiungi_log_radio(mio, f"Paziente valutato: PA {pa}, FC {fc}")
                    st.success("Dati inviati.")
