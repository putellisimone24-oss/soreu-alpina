# =========================================================
# SOREU ALPINA - VERSIONE PRO COMPLETA
# CENTRALE AVANZATA + MEZZI + ECG + CONSUMI + EVENTI DINAMICI
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS log_eventi
                 (timestamp TEXT, tipo TEXT, descrizione TEXT)''')

    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [
            ('admin', 'admin', 0, 'Admin'),
            ('operatore', '1234', 0, 'Operatore')
        ]
        c.executemany("INSERT INTO utenti VALUES (?,?,?,?)", utenti_iniziali)

    conn.commit()
    conn.close()

init_db()

# =========================================================
# UTENTI
# =========================================================

def get_utente_db(username):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT * FROM utenti WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res

# =========================================================
# FUNZIONI
# =========================================================

def genera_tracciato_ecg():
    x = np.linspace(0, 10, 500)
    y = np.sin(x*1.2*2*np.pi)+0.5*np.sin(x*2.4*2*np.pi)+np.random.normal(0,0.05,500)
    return pd.DataFrame({"Tempo":x,"mV":y})


def log_evento(tipo, descrizione):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("INSERT INTO log_eventi VALUES (?,?,?)",
              (datetime.now().strftime("%H:%M:%S"), tipo, descrizione))
    conn.commit()
    conn.close()

# =========================================================
# SESSION STATE
# =========================================================

st.set_page_config(page_title="SOREU PRO", layout="wide")

if 'utente' not in st.session_state: st.session_state.utente=None
if 'ruolo' not in st.session_state: st.session_state.ruolo=None
if 'missioni' not in st.session_state: st.session_state.missioni={}
if 'ecg' not in st.session_state: st.session_state.ecg={}
if 'log_radio' not in st.session_state: st.session_state.log_radio=[]
if 'auto_eventi' not in st.session_state: st.session_state.auto_eventi=False

# MEZZI
if 'mezzi' not in st.session_state:
    st.session_state.mezzi={
        "MSA1":{"stato":"Libero","tipo":"MSA","lat":45.6,"lon":9.6},
        "MSB1":{"stato":"Libero","tipo":"MSB","lat":45.7,"lon":9.7}
    }

# CONSUMI
if 'consumi' not in st.session_state:
    st.session_state.consumi={m:{"O2":100,"Elettrodi":20} for m in st.session_state.mezzi}

# CHECKLIST
if 'check' not in st.session_state:
    st.session_state.check={m:{"A":False,"B":False,"C":False} for m in st.session_state.mezzi}

# STATS
if 'stats' not in st.session_state:
    st.session_state.stats={"missioni":0,"chiuse":0}

# =========================================================
# LOGIN
# =========================================================

if st.session_state.utente is None:
    u=st.text_input("User")
    p=st.text_input("Pass",type="password")
    if st.button("Login"):
        user=get_utente_db(u)
        if user and user[1]==p:
            st.session_state.utente=u
            st.rerun()
    st.stop()

# =========================================================
# MENU
# =========================================================

if st.session_state.ruolo is None:
    if st.button("CENTRALE"): st.session_state.ruolo="centrale"; st.rerun()
    if st.button("MEZZO"): st.session_state.ruolo="mezzo"; st.rerun()

# =========================================================
# CENTRALE AVANZATA
# =========================================================

elif st.session_state.ruolo=="centrale":

    st.header("CENTRALE OPERATIVA AVANZATA")

    col1,col2=st.columns(2)

    # GENERATORE EVENTI
    with col1:
        st.subheader("EVENTI")

        if st.button("Nuovo Evento Manuale"):
            ev=f"T{random.randint(100,999)}"
            st.session_state.missioni[ev]={
                "stato":"attivo",
                "codice":random.choice(["VERDE","GIALLO","ROSSO"]),
                "target":f"Via {random.randint(1,100)}"
            }
            st.session_state.stats['missioni']+=1
            log_evento("EVENTO","Creato "+ev)

        if st.button("Toggle Auto Eventi"):
            st.session_state.auto_eventi = not st.session_state.auto_eventi

        if st.session_state.auto_eventi and random.random()<0.1:
            ev=f"T{random.randint(100,999)}"
            st.session_state.missioni[ev]={"stato":"attivo"}
            log_evento("AUTO","Evento automatico")

    # ASSEGNAZIONE MEZZI
    with col2:
        st.subheader("ASSEGNAZIONE")

        for ev,data in st.session_state.missioni.items():
            st.write(ev, data)
            mezzo=st.selectbox(f"Mezzo per {ev}", list(st.session_state.mezzi.keys()), key=ev)
            if st.button(f"Assegna {ev}"):
                st.session_state.mezzi[mezzo]['stato']="In missione"
                data['mezzo']=mezzo
                log_evento("ASSEGNA","{ev} -> {mezzo}")

    # RADIO
    st.subheader("RADIO")
    msg=st.text_input("Messaggio radio")
    if st.button("Invia Radio"):
        st.session_state.log_radio.insert(0,f"{datetime.now().strftime('%H:%M:%S')} - {msg}")

    for r in st.session_state.log_radio[:10]:
        st.write(r)

    # ECG VIEW
    st.subheader("ECG DA MEZZI")
    for m,ecg in st.session_state.ecg.items():
        st.line_chart(ecg)

# =========================================================
# MEZZO
# =========================================================

elif st.session_state.ruolo=="mezzo":

    m=st.selectbox("Mezzo", list(st.session_state.mezzi.keys()))

    st.title(m)

    cons=st.session_state.consumi[m]
    chk=st.session_state.check[m]

    st.subheader("CONSUMI")
    st.write(cons)

    if st.button("Rifornisci"):
        st.session_state.consumi[m]={"O2":100,"Elettrodi":20}

    st.subheader("CHECKLIST")
    chk['A']=st.checkbox("Airway",value=chk['A'])
    chk['B']=st.checkbox("Breathing",value=chk['B'])
    chk['C']=st.checkbox("Circulation",value=chk['C'])

    completa=all(chk.values())

    st.subheader("ECG")
    if st.button("Invia ECG"):
        if cons['Elettrodi']>=4:
            cons['Elettrodi']-=4
            st.session_state.ecg[m]=genera_tracciato_ecg()

    if m in st.session_state.ecg:
        st.line_chart(st.session_state.ecg[m])

    st.subheader("STATI")

    if st.button("1 PARTENZA"):
        st.success("Partito")

    if st.button("2 ARRIVO"):
        st.success("Arrivato")

    if st.button("3 OSPEDALE",disabled=not completa):
        st.success("Verso ospedale")

    if st.button("4 CHIUDI"):
        cons['O2']=max(0,cons['O2']-10)
        st.session_state.stats['chiuse']+=1
        st.success("Chiuso")

# =========================================================
# DASHBOARD
# =========================================================

st.sidebar.header("STATISTICHE")
st.sidebar.write(st.session_state.stats)
