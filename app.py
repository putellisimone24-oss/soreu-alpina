# =========================================================
# SOREU ALPINA - SIMULATORE REALISTICO TOTALE
# VERSIONE ESTESA (CENTRALE + MEZZI + GPS + OSPEDALI + TEMPI REALI)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import sqlite3
from datetime import datetime

# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, ruolo TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS log_eventi
                 (timestamp TEXT, tipo TEXT, descrizione TEXT)''')

    if c.execute("SELECT COUNT(*) FROM utenti").fetchone()[0] == 0:
        c.executemany("INSERT INTO utenti VALUES (?,?,?)",[
            ('admin','admin','Admin'),
            ('operatore','1234','Operatore')
        ])

    conn.commit()
    conn.close()

init_db()

# =========================================================
# FUNZIONI CORE
# =========================================================

def log_evento(tipo, descrizione):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("INSERT INTO log_eventi VALUES (?,?,?)",
              (datetime.now().strftime("%H:%M:%S"), tipo, descrizione))
    conn.commit()
    conn.close()


def distanza(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2) * 111


def genera_ecg():
    x = np.linspace(0,10,500)
    y = np.sin(x*2*np.pi)+np.random.normal(0,0.1,500)
    return pd.DataFrame({"t":x,"ecg":y})

# =========================================================
# SESSION STATE
# =========================================================

st.set_page_config(layout="wide")

for key,default in {
    'user':None,
    'ruolo':None,
    'missioni':{},
    'mezzi':{},
    'ospedali':{},
    'ecg':{},
    'consumi':{},
    'check':{},
    'stats':{"missioni":0,"chiuse":0},
    'radio':[]
}.items():
    if key not in st.session_state:
        st.session_state[key]=default

# INIT MEZZI
if not st.session_state.mezzi:
    st.session_state.mezzi={
        "MSA1":{"lat":45.6,"lon":9.6,"stato":"Libero","vel":60},
        "MSB1":{"lat":45.7,"lon":9.7,"stato":"Libero","vel":50}
    }

# INIT OSPEDALI
if not st.session_state.ospedali:
    st.session_state.ospedali={
        "Papa Giovanni":{"lat":45.68,"lon":9.62,"tipo":"DEA2"},
        "Gavazzeni":{"lat":45.69,"lon":9.68,"tipo":"DEA1"}
    }

# INIT CONSUMI
for m in st.session_state.mezzi:
    if m not in st.session_state.consumi:
        st.session_state.consumi[m]={"O2":100,"Elettrodi":20}

# INIT CHECK
for m in st.session_state.mezzi:
    if m not in st.session_state.check:
        st.session_state.check[m]={"A":False,"B":False,"C":False}

# =========================================================
# LOGIN
# =========================================================

if st.session_state.user is None:
    u=st.text_input("User")
    p=st.text_input("Pass",type="password")
    if st.button("Login"):
        conn=sqlite3.connect('centrale.db')
        c=conn.cursor()
        res=c.execute("SELECT * FROM utenti WHERE username=?",(u,)).fetchone()
        conn.close()
        if res and res[1]==p:
            st.session_state.user=u
            st.rerun()
    st.stop()

# =========================================================
# MENU
# =========================================================

if st.session_state.ruolo is None:
    if st.button("CENTRALE"): st.session_state.ruolo="centrale"; st.rerun()
    if st.button("MEZZO"): st.session_state.ruolo="mezzo"; st.rerun()

# =========================================================
# CENTRALE REALISTICA
# =========================================================

elif st.session_state.ruolo=="centrale":

    st.title("CENTRALE OPERATIVA REALISTICA")

    # NUOVO EVENTO
    if st.button("NUOVO EVENTO"):
        ev=f"T{random.randint(100,999)}"
        lat=random.uniform(45.5,45.8)
        lon=random.uniform(9.5,9.8)
        st.session_state.missioni[ev]={
            "lat":lat,
            "lon":lon,
            "stato":"attivo",
            "mezzo":None
        }
        st.session_state.stats['missioni']+=1

    # ASSEGNAZIONE AUTOMATICA
    for ev,data in st.session_state.missioni.items():
        if data['mezzo'] is None:
            best=None
            best_d=999
            for m,d in st.session_state.mezzi.items():
                if d['stato']=="Libero":
                    dist=distanza(d['lat'],d['lon'],data['lat'],data['lon'])
                    if dist<best_d:
                        best=m
                        best_d=dist
            if best:
                data['mezzo']=best
                st.session_state.mezzi[best]['stato']="Occupato"

    # MAPPA
    df=pd.DataFrame([
        {"lat":d['lat'],"lon":d['lon']} for d in st.session_state.mezzi.values()
    ])
    st.map(df)

    st.write(st.session_state.missioni)

    # RADIO
    msg=st.text_input("Radio")
    if st.button("Invia"):
        st.session_state.radio.insert(0,msg)

    for r in st.session_state.radio[:5]:
        st.write(r)

# =========================================================
# MEZZO REALISTICO
# =========================================================

elif st.session_state.ruolo=="mezzo":

    m=st.selectbox("Mezzo",list(st.session_state.mezzi.keys()))
    mezzo=st.session_state.mezzi[m]
    cons=st.session_state.consumi[m]
    chk=st.session_state.check[m]

    st.title(f"{m}")

    # GPS MOVIMENTO
    if mezzo['stato']=="Occupato":
        mezzo['lat']+=random.uniform(-0.001,0.001)
        mezzo['lon']+=random.uniform(-0.001,0.001)

    st.write("Posizione:",mezzo['lat'],mezzo['lon'])

    # CONSUMI
    st.write(cons)

    # CHECKLIST
    chk['A']=st.checkbox("A",value=chk['A'])
    chk['B']=st.checkbox("B",value=chk['B'])
    chk['C']=st.checkbox("C",value=chk['C'])

    completa=all(chk.values())

    # ECG
    if st.button("ECG"):
        if cons['Elettrodi']>=4:
            cons['Elettrodi']-=4
            st.session_state.ecg[m]=genera_ecg()

    if m in st.session_state.ecg:
        st.line_chart(st.session_state.ecg[m])

    # STATI
    if st.button("CHIUDI"):
        mezzo['stato']="Libero"
        cons['O2']-=10
        st.session_state.stats['chiuse']+=1

# =========================================================
# DASHBOARD
# =========================================================

st.sidebar.write(st.session_state.stats)
