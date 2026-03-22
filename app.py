import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
import os

# --- 1. ADATBÁZIS INICIALIZÁLÁSA ---
def init_db():
    conn = sqlite3.connect('terc_vegleges.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS normak 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, nev TEXT, egyseg TEXT, anyag REAL, norma REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projekt_tetelek 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, norma_id INTEGER, mennyiseg REAL)''')
    c.execute("SELECT count(*) FROM normak")
    if c.fetchone()[0] == 0:
        alap_normak = [
            ('21-001', 'Vázkerámia falazóblokk 30-as', 'm2', 5500, 1.2),
            ('11-002', 'Aljzatbeton készítése C16/20', 'm3', 32000, 2.5),
            ('33-005', 'Belső falfelület festése diszperziós festékkel', 'm2', 850, 0.4),
            ('41-001', 'Homlokzati csőállvány építése', 'm2', 1200, 0.6)
        ]
        c.executemany("INSERT INTO normak (kod, nev, egyseg, anyag, norma) VALUES (?,?,?,?,?)", alap_normak)
    conn.commit()
    conn.close()

init_db()

# --- 2. OLDAL BEÁLLÍTÁSAI ---
st.set_page_config(page_title="Digitális TERC Oktató", layout="wide", page_icon="🏗️")
st.title("🏗️ Digitális TERC - Költségvetés Készítő")
st.write("Oktatási verzió v4.0 | Műszaki és gazdasági számítások")

# --- 3. ÚJ TÉTEL HOZZÁADÁSA ---
with st.expander("➕ ÚJ TÉTEL HOZZÁADÁSA A NORMA GYŰJTEMÉNYBE"):
    with st.form("uj_tetel_form"):
        col1, col2 = st.columns(2)
        with col1:
            uj_kod = st.text_input("Tételszám (pl. 21-002)")
            uj_nev = st.text_input("Megnevezés")
            uj_egyseg = st.selectbox("Egység", ["m2", "m3", "fm", "db", "kg"])
        with col2:
            uj_anyag = st.number_input("Anyag egységár (Ft)", min_value=0, value=1000)
            uj_norma = st.number_input("Normaidő (óra/egység)", min_value=0.0, value=1.0, step=0.1)
        if st.form_submit_button("💾 Tétel mentése"):
            conn = sqlite3.connect('terc_vegleges.db')
            c = conn.cursor()
            c.execute("INSERT INTO normak (kod, nev, egyseg, anyag, norma) VALUES (?,?,?,?,?)", (uj_kod, uj_nev, uj_egyseg, uj_anyag, uj_norma))
            conn.commit()
            conn.close()
            st.success("Tétel elmentve!")
            st.rerun()

# --- 4. KÖLTSÉGVETÉS ÖSSZEÁLLÍTÁSA ---
st.header("📋 Aktuális projekt összeállítása")
conn = sqlite3.connect('terc_vegleges.db')
normak_df = pd.read_sql_query("SELECT * FROM normak", conn)

if not normak_df.empty:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        kivalasztott_nev = st.selectbox("Válassz tételt a gyűjteményből:", normak_df['nev'].tolist())
    with col_b:
        mennyiseg = st.number_input("Mennyiség:", min_value=0.1, value=1.0, step=0.1)
    if st.button("📥 Hozzáadás a projekthez"):
        t_id = normak_df[normak_df['nev'] == kivalasztott_nev]['id'].values[0]
        c = conn.cursor()
        c.execute("INSERT INTO projekt_tetelek (norma_id, mennyiseg) VALUES (?,?)", (int(t_id), mennyiseg))
        conn.commit()
        st.rerun()
conn.close()

# --- 5. TÁBLÁZAT ÉS ÖSSZESÍTÉS ---
st.subheader("📊 Projekt tételei")
conn = sqlite3.connect('terc_vegleges.db')
query = "SELECT n.kod, n.nev, p.mennyiseg, n.egyseg, n.anyag, n.norma, (p.mennyiseg * n.anyag) as ossz_anyag, (p.mennyiseg * n.norma) as ossz_munkaora FROM projekt_tetelek p JOIN normak n ON p.norma_id = n.id"
projekt_df = pd.read_sql_query(query, conn)
conn.close()

if not projekt_df.empty:
    st.dataframe(projekt_df, use_container_width=True)
    osszes_anyag = projekt_df['ossz_anyag'].sum()
    osszes_ora = projekt_df['ossz_munkaora'].sum()
    c1, c2 = st.columns(2)
    c1.metric("Összes anyagköltség", f"{osszes_anyag:,.0f} Ft".replace(",", " "))
    c2.metric("Összes munkaidő szükséglet", f"{osszes_ora:.2f} óra")
    if st.button("🗑️ Projekt ürítése"):
        conn = sqlite3.connect('terc_vegleges.db')
        conn.execute("DELETE FROM projekt_tetelek")
        conn.commit()
        conn.close()
        st.rerun()
else:
    st.info("Még nincsenek tételek a projektben.")
