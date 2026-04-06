import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. SISTEMA DI SICUREZZA E GESTIONE ACCESSI (IAM)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

# Inizializzazione Database Utenti (Persistente nella sessione)
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin", "cambio_obbligatorio": False, "ruolo": "Admin"},
        "operatore.test": {"pw": "118", "cambio_obbligatorio": True, "ruolo": "Operatore"}
    }

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# Schermata di Login
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Accesso Sistema")
    
    if st.session_state.fase_cambio_pw:
        st.warning("⚠️ Primo accesso: Cambia la tua password per continuare.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI", type="primary"):
            if n_p == c_p and len(n_p) >= 4:
                u = st.session_state.temp_user
                st.session_state.utenti_db[u]["pw"] = n_p
                st.session_state.utenti_db[u]["cambio_obbligatorio"] = False
                st.session_state.utente_connesso = u
                st.rerun()
            else:
                st.error("Le password non coincidono o sono troppo brevi (min 4 car).")
    else:
        u_in = st.text_input("ID Utente").lower()
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
# 2. FUNZIONI TECNICHE E SUONI
# =========================================================

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
    if tempo_minuti < 1: tempo_minuti = 1
    return round(distanza, 1), tempo_minuti

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# =========================================================
# 3. DATABASE (MEZZI, OSPEDALI, EVENTI)
# =========================================================

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
    {"sintomi": "Bambino di 4 anni con febbre a 39.5 e convulsioni in atto.", "codice_reale": "ROSSO", "patologia": "Convulsione Febbrile", "necessita_msa": True},
    {"sintomi": "Anziana scivolata in casa, impossibilitata ad alzarsi, riferisce lieve dolore all'anca.", "codice_reale": "VERDE", "patologia": "Caduta in casa", "necessita_msa": False},
    {"sintomi": "Paziente trovato a terra incosciente, respiro agonico (gasping).", "codice_reale": "ROSSO", "patologia": "Arresto Cardiaco", "necessita_msa": True}
]

# =========================================================
# 4. INIZIALIZZAZIONE SESSIONE E LOGICA AUTOMATICA
# =========================================================

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

def aggiorna_stati_automatici():
    now = time.time()
    voci_da_rimuovere = []
    for m_nome, miss in st.session_state.missioni.items():
        creazione = miss["timestamp_creazione"]
        db = st.session_state.database_mezzi
        mult = st.session_state.time_mult
        
        fase1, fase2, faseOsp, fase3, fase4, durata = 30/mult, 60/mult, 60/mult, 120/mult, 180/mult, 240/mult
        tempo_trascorso = now - creazione
        
        if tempo_trascorso < fase1:
            if db[m_nome]["stato"] != "1 - Partenza da sede":
                db[m_nome]["stato"] = "1 - Partenza da sede"; db[m_nome]["colore"] = "🟡"
                aggiungi_log_radio(m_nome, "STATO 1: Partenza da sede direzione luogo intervento.")
        elif tempo_trascorso < fase2:
            if db[m_nome]["stato"] != "2 - Arrivato su posto":
                db[m_nome]["stato"] = "2 - Arrivato su posto"
                aggiungi_log_radio(m_nome, "STATO 2: Arrivati sul luogo dell'evento.")
        elif tempo_trascorso >= faseOsp and tempo_trascorso < fase3:
            if not miss.get("richiesto_ospedale", False):
                st.session_state.notifiche_centrale.append(f"🩺 {m_nome} richiede ospedale!")
                aggiungi_log_radio(m_nome, "Paziente valutato. Richiediamo ospedale di destinazione.")
                riproduci_suono_notifica()
                st.session_state.missioni[m_nome]["richiesto_ospedale"] = True
        elif tempo_trascorso >= fase3 and tempo_trascorso < fase4:
            if db[m_nome]["stato"] != "3 - Partenza per ospedale":
                db[m_nome]["stato"] = "3 - Partenza per ospedale"
                dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                aggiungi_log_radio(m_nome, f"STATO 3: Paziente a bordo. Direzione {dest}.")
        elif tempo_trascorso >= fase4 and tempo_trascorso < durata:
            if db[m_nome]["stato"] != "Arrivati in Ospedale":
                db[m_nome]["stato"] = "Arrivati in Ospedale"
                dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
                aggiungi_log_radio(m_nome, f"Arrivati a destinazione presso {dest}.")
        elif tempo_trascorso >= durata:
            db[m_nome]["stato"], db[m_nome]["colore"] = "Libero in Sede", "🟢"
            aggiungi_log_radio(m_nome, "Fine missione. Mezzo LIBERO.")
            dest = miss.get("ospedale_confermato", miss["ospedale_assegnato"])
            if dest in st.session_state.database_ospedali:
                st.session_state.database_ospedali[dest]["pazienti"] = min(st.session_state.database_ospedali[dest]["max"], st.session_state.database_ospedali[dest]["pazienti"] + 1)
            voci_da_rimuovere.append(m_nome)
            
    for v in voci_da_rimuovere: del st.session_state.missioni[v]

if st.session_state.auto_mode and st.session_state.missioni and st.session_state.turno_iniziato:
    aggiorna_stati_automatici()

# Generazione Chiamate
tempo_base = 120
tempo_necessario = tempo_base / st.session_state.time_mult
if st.session_state.turno_iniziato and (time.time() - st.session_state.last_mission_time > tempo_necessario):
    if not st.session_state.evento_corrente:
        scelta_indirizzo = random.choice(database_indirizzi)
        scelta_clinica = random.choice(scenari_clinici)
        st.session_state.evento_corrente = {**scelta_indirizzo, **scelta_clinica}
        st.session_state.last_mission_time = time.time()
        st.session_state.log_chiamate.append(f"{scelta_indirizzo['via']} ({scelta_indirizzo['comune']})")
        st.session_state.suono_riprodotto = False

# =========================================================
# 5. UI - BARRA LATERALE E HEADER
# =========================================================
col_titolo, col_orologio = st.columns([3, 1])
with col_titolo: st.title("🎧 SOREU Alpina - Sala Operativa")
with col_orologio: 
    st.metric(label="🕒 Orario", value=datetime.now().strftime("%H:%M:%S"))
    if st.button("🚪 LOGOUT", use_container_width=True):
        st.session_state.utente_connesso = None
        st.rerun()

with st.sidebar:
    st.header(f"👤 {st.session_state.utente_connesso}")
    if st.session_state.utente_connesso == "admin":
        with st.expander("🛠️ Gestione Utenti"):
            nuovo_u = st.text_input("Nuovo ID")
            nuova_p = st.text_input("Password", type="password")
            if st.button("Aggiungi Operatore"):
                st.session_state.utenti_db[nuovo_u] = {"pw": nuova_p, "cambio_obbligatorio": True, "ruolo": "Operatore"}
                st.success(f"Utente {nuovo_u} creato!")

    st.divider()
    if st.button("⬅️ Cambio Ruolo Operativo", use_container_width=True):
        st.session_state.scrivania_selezionata = None
        st.session_state.ruolo = None
        st.rerun()
    
    st.divider()
    st.subheader("🕹️ Opzioni")
    st.session_state.auto_mode = st.toggle("🤖 Automatizza Equipaggi", value=st.session_state.auto_mode)
    vel = st.radio("Cadenza Chiamate", ["Normale", "2X", "5X", "10X"])
    st.session_state.time_mult = 1.0 if vel == "Normale" else (2.0 if vel == "2X" else (5.0 if vel == "5X" else 10.0))

# =========================================================
# 6. SCHERMATE OPERATIVE
# =========================================================

# Selezione Scrivania
if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione di Lavoro")
    col_a, col_b, col_c = st.columns(3)
    for i, col in enumerate([col_a, col_b, col_c, col_a, col_b, col_c]):
        if col.button(f"🖥️ Scrivania {i+1}", use_container_width=True):
            st.session_state.scrivania_selezionata = i+1; st.session_state.ruolo = "centrale"; st.rerun()
    if st.button("🚑 Accedi come Equipaggio Mezzo (Esterno)", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# Inizio Turno
elif not st.session_state.turno_iniziato and st.session_state.ruolo == "centrale":
    st.info(f"📍 Scrivania {st.session_state.scrivania_selezionata} pronta.")
    if st.button("🟢 INIZIA TURNO", type="primary", use_container_width=True):
        st.session_state.turno_iniziato = True; st.rerun()

# INTERFACCIA CENTRALE
elif st.session_state.ruolo == "centrale":
    tab_invio, tab_risorse, tab_ps = st.tabs(["📝 Nuove Missioni", "🚑 Stato Risorse", "🏥 Monitoraggio PS"])
    
    with tab_invio:
        c1, c2 = st.columns([1.5, 2])
        with c1:
            st.header("📋 Chiamate")
            if st.button("🔔 Forza Chiamata", use_container_width=True):
                st.session_state.evento_corrente = {**random.choice(database_indirizzi), **random.choice(scenari_clinici)}
                st.session_state.suono_riprodotto = False; st.rerun()
            
            if st.session_state.evento_corrente:
                if not st.session_state.suono_riprodotto: riproduci_suono_allarme(); st.session_state.suono_riprodotto = True
                ev = st.session_state.evento_corrente
                st.error(f"📍 TARGET: {ev['via']}, {ev['comune']}")
                st.info(f"🗣️ SINTOMI: {ev['sintomi']}")
                
                codice = st.selectbox("Codice Gravità", ["ROSSO", "GIALLO", "VERDE"])
                mezzi_liberi = []
                for n, d in st.session_state.database_mezzi.items():
                    if d["stato"] == "Libero in Sede":
                        dist, tempo = calcola_distanza_e_tempo(d["lat"], d["lon"], ev["lat"], ev["lon"], (d["tipo"]=="ELI"))
                        mezzi_liberi.append({"Mezzo": n, "Tipo": d["tipo"], "Tempo (min)": tempo})
                
                if mezzi_liberi:
                    df_liberi = pd.DataFrame(mezzi_liberi).sort_values("Tempo (min)")
                    st.dataframe(df_liberi, use_container_width=True, hide_index=True)
                    scelti = st.multiselect("Seleziona Mezzi", df_liberi["Mezzo"].tolist())
                    osp = st.selectbox("Ospedale Pre-allerta", list(st.session_state.database_ospedali.keys()))
                    
                    if st.button("🚀 INVIA", type="primary", use_container_width=True):
                        for m in scelti:
                            st.session_state.missioni[m] = {
                                "target": f"{ev['via']}, {ev['comune']}", "lat": ev['lat'], "lon": ev['lon'],
                                "codice": codice, "ospedale_assegnato": osp, "timestamp_creazione": time.time()
                            }
                            if not st.session_state.auto_mode:
                                st.session_state.database_mezzi[m]["stato"] = "1 - Partenza"; st.session_state.database_mezzi[m]["colore"] = "🟡"
                        st.session_state.evento_corrente = None; st.rerun()

        with c2:
            st.header("🗺️ Mappa Area")
            st.map(pd.DataFrame([{"lat": d["lat"], "lon": d["lon"]} for d in st.session_state.database_mezzi.values()]))
            st.subheader("📻 Registro Radio")
            st.text_area("Comunicazioni", value="\n".join(st.session_state.registro_radio[:15]), height=150, disabled=True)

    with tab_risorse:
        for m, d in st.session_state.database_mezzi.items():
            st.write(f"**{m}**: {d['stato']} {d['colore']}")

    with tab_ps:
        for osp, d in st.session_state.database_ospedali.items():
            st.write(f"**{osp}** ({d['pazienti']}/{d['max']})")
            st.progress(d['pazienti']/d['max'])
            if st.button("Libera Posto", key=f"lib_{osp}"):
                st.session_state.database_ospedali[osp]["pazienti"] = max(0, d["pazienti"]-1); st.rerun()

# INTERFACCIA MEZZO
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Identificazione Mezzo", list(st.session_state.database_mezzi.keys()))
        if st.button("LOGIN"): st.rerun()
    else:
        mio = st.session_state.mezzo_selezionato
        dati = st.session_state.database_mezzi[mio]
        st.header(f"📟 Terminale: {mio}")
        st.write(f"Stato: **{dati['stato']}**")
        
        in_m = mio in st.session_state.missioni
        dis = st.session_state.auto_mode or not in_m
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚨 1 - Partenza", use_container_width=True, disabled=dis):
                dati["stato"] = "1 - Partenza"; aggiungi_log_radio(mio, "Partenza sede."); st.rerun()
            if st.button("🏥 3 - Partenza Ospedale", use_container_width=True, disabled=dis):
                dati["stato"] = "3 - Partenza Ospedale"; aggiungi_log_radio(mio, "In viaggio verso PS."); st.rerun()
        with c2:
            if st.button("📍 2 - Arrivo Posto", use_container_width=True, disabled=dis):
                dati["stato"] = "2 - Arrivato su posto"; aggiungi_log_radio(mio, "Sul posto."); st.rerun()
            if st.button("🏁 4 - Fine (Libero)", type="primary", use_container_width=True, disabled=dis):
                dati["stato"], dati["colore"] = "Libero in Sede", "🟢"
                aggiungi_log_radio(mio, "Mezzo LIBERO."); del st.session_state.missioni[mio]; st.rerun()
        
        if in_m:
            st.divider()
            st.subheader("🩺 Parametri Vitali")
            pa = st.slider("Pressione", 50, 200, 120)
            fc = st.slider("FC", 30, 180, 80)
            if st.button("Invia Parametri"):
                st.session_state.notifiche_centrale.append(f"Parametri da {mio}: PA {pa}, FC {fc}")
                st.toast("Parametri trasmessi!")
