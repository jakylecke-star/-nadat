import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
import os

# --- 1. ADATBÁZIS KEZELÉS ---
# --- 1. ADATBÁZIS KEZELÉS ---
conn = sqlite3.connect('terc_oktatas.db', check_same_thread=False)
c = conn.cursor()

# Táblák létrehozása
c.execute('CREATE TABLE IF NOT EXISTS normak (id INTEGER PRIMARY KEY, kod TEXT, nev TEXT, egyseg TEXT, anyag REAL, norma REAL)')
c.execute('CREATE TABLE IF NOT EXISTS projekt_tetelek (id INTEGER PRIMARY KEY, norma_id INTEGER, mennyiseg REAL)')

# ALAPADATOK FELTÖLTÉSE (Ha üres a tábla)
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

    # Ez a rész nézi meg, hogy üres-e a lista. Ha igen, beleírja az alapokat.
    c.execute("SELECT count(*) FROM normagyujtemeny")
    if c.fetchone()[0] == 0:
        alap_tetelek = [
            ('Falazás', '21-001', 'Vázkerámia falazóblokk 30-as', 'm2', 5500, 1.2),
            ('Betonozás', '11-002', 'Aljzatbeton készítése C16/20', 'm3', 32000, 2.5),
            ('Festés', '33-005', 'Belső falfelület festése diszperziós festékkel', 'm2', 850, 0.4),
            ('Állványozás', '41-001', 'Homlokzati csőállvány építése', 'm2', 1200, 0.6)
        ]
        c.executemany("INSERT INTO normagyujtemeny (szakag, tetelszam, megnevezes, egyseg, anyag_ar, normatido) VALUES (?,?,?,?,?,?)", alap_tetelek)

    conn.commit()
    conn.close()

# --- 2. OLDAL BEÁLLÍTÁSAI ---
st.set_page_config(page_title="Digitális TERC Oktató", layout="wide", page_icon="🏗️")

# Egyedi stílus (TERC-kék fejléc)
st.markdown("""
    <style>
    /* Ez a rész nem fog látszódni, csak a paneleket színezi át */
    [data-testid="stMetric"] {
        background-color: #1e2129;
        border: 1px solid #4a4a4a;
        padding: 15px;
        border-radius: 10px;
    }
    [data-testid="stMetricValue"] {
        color: #00ff00 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)
st.title("🏗️ Digitális TERC - Költségvetés Készítő")
st.caption("Oktatási verzió v3.0 | Műszaki és gazdasági számítások")

# --- 3. ADMINISZTRÁCIÓ (ÚJ TÉTELEK BEVITELE) ---
with st.expander("➕ ÚJ TÉTEL HOZZÁADÁSA A NORMAGYŰJTEMÉNYBE"):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        uj_kat = st.selectbox("Szakág", ["Falazás", "Hőszigetelés", "Festés", "Burkolás", "Tetőszerkezet", "Egyéb"])
        uj_kod = st.text_input("Tételszám (pl. 21-002)")
    with col_b:
        uj_nev = st.text_input("Megnevezés (Gyártó, típus, méret)")
        uj_egyseg = st.selectbox("Egység", ["m2", "m3", "fm", "db", "kg"])
    with col_c:
        uj_anyag = st.number_input("Anyag egységár (Ft)", min_value=0, value=1000)
        uj_munka = st.number_input("Normaidő (óra/egység)", min_value=0.0, value=1.0, format="%.3f")
    
    if st.button("💾 Tétel mentése az adatbázisba"):
        if uj_nev and uj_kod:
            c.execute("INSERT INTO normak (kod, nev, egyseg, anyag, munka, kategoria) VALUES (?,?,?,?,?,?)",
                      (uj_kod, uj_nev, uj_egyseg, uj_anyag, uj_munka, uj_kat))
            conn.commit()
            st.success(f"'{uj_nev}' sikeresen rögzítve!")
            st.rerun()
        else:
            st.error("Kérlek töltsd ki a nevet és a kódot!")

st.divider()

# --- 4. KÖLTSÉGVETÉS ÖSSZEÁLLÍTÁSA ---
oraber = st.sidebar.number_input("🏗️ Rezsióradíj (Ft/óra)", value=5500, step=100)

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Tétel választó")
    n_df = pd.read_sql_query("SELECT * FROM normak", conn)
    
    if not n_df.empty:
        valaszthato_kat = n_df['kategoria'].unique()
        kat = st.selectbox("Szakág szűrése:", valaszthato_kat)
        
        szurt_df = n_df[n_df['kategoria'] == kat]
        valasztott_tétel = st.selectbox("Konkrét tétel:", szurt_df['nev'].tolist())
        
        t_adat = szurt_df[szurt_df['nev'] == valasztott_tétel].iloc[0]
        st.info(f"Kód: {t_adat['kod']} | Anyag: {t_adat['anyag']:,} Ft | Norma: {t_adat['munka']} óra")
        
        mennyiseg = st.number_input(f"Mennyiség ({t_adat['egyseg']})", min_value=0.01, value=1.0)
        
        if st.button("➕ Hozzáadás a projekthez"):
            c.execute("INSERT INTO projekt_tetelek (norma_id, mennyiseg) VALUES (?,?)", (int(t_adat['id']), mennyiseg))
            conn.commit()
            st.toast("Tétel hozzáadva!")

with col2:
    st.subheader("Aktuális projekt tételei")
    df_projekt = pd.read_sql_query("""
        SELECT n.kategoria as 'Szakág', n.kod as 'Tételszám', n.nev as 'Megnevezés', 
        p.mennyiseg as 'Mennyiség', n.egyseg as 'Egység', n.anyag as 'Anyag e.ár', n.munka as 'Normaidő'
        FROM projekt_tetelek p JOIN normak n ON p.norma_id = n.id""", conn)

    if not df_projekt.empty:
        df_projekt['Anyag összesen'] = df_projekt['Mennyiség'] * df_projekt['Anyag e.ár']
        df_projekt['Munkadíj összesen'] = df_projekt['Mennyiség'] * df_projekt['Normaidő'] * oraber
        df_projekt['Mindösszesen'] = df_projekt['Anyag összesen'] + df_projekt['Munkadíj összesen']
        
        st.dataframe(df_projekt, use_container_width=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Anyag összesen", f"{df_projekt['Anyag összesen'].sum():,.0f} Ft")
        m2.metric("Munkadíj összesen", f"{df_projekt['Munkadíj összesen'].sum():,.0f} Ft")
        m3.metric("Projekt Végösszeg", f"{df_projekt['Mindösszesen'].sum():,.0f} Ft", delta_color="inverse")

        # --- EXCEL EXPORT ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_projekt.to_excel(writer, index=False, sheet_name='Költségvetés')
        
        st.download_button(
            label="📥 Költségvetés exportálása Excelbe",
            data=output.getvalue(),
            file_name="terc_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.write("Még nincsenek tételek a listában.")

if st.sidebar.button("🗑️ Projekt alaphelyzetbe"):
    c.execute("DELETE FROM projekt_tetelek")
    conn.commit()
    st.rerun()
