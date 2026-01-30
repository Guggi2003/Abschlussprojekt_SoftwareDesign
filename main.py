import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mechanical_system import MechanicalSystem
from topology_optimizer import TopologyOptimizationController

# --- Seitenkonfiguration ---
st.set_page_config(page_title="Topologieoptimierung", layout="wide")

st.title("Topologieoptimierung von 2D-Strukturen")

# --- Sidebar: Einstellungen ---
st.sidebar.header("Einstellungen")
width = st.sidebar.number_input("Breite (Anzahl Knoten)", min_value=2, value=10)
height = st.sidebar.number_input("Höhe (Anzahl Knoten)", min_value=2, value=5)
target_ratio = st.sidebar.slider("Ziel-Masserate", 0.1, 1.0, 0.5)

# --- Session State initialisieren (für Persistenz während Klicks) ---
if 'system' not in st.session_state:
    st.session_state['system'] = None

# --- Buttons ---
col1, col2 = st.columns(2)

with col1:
    if st.button("Neues Modell erstellen"):
        sys = MechanicalSystem(width, height)
        sys.create_initial_mesh()
        # TODO: Hier standardmäßig Lager und Kräfte setzen (z.B. MBB Balken)
        st.session_state['system'] = sys
        st.success("Modell erstellt!")

with col2:
    if st.button("Optimierungsschritt durchführen"):
        if st.session_state['system'] is not None:
            optimizer = TopologyOptimizationController(st.session_state['system'], target_ratio)
            optimizer.run_optimization_step()
            st.success(f"Schritt durchgeführt.")
        else:
            st.error("Bitte erst ein Modell erstellen.")

# --- Visualisierung ---
st.header("Visualisierung")
if st.session_state['system'] is not None:
    # Platzhalter für den Plot
    fig, ax = plt.subplots()
    
    # TODO: Iteriere über system.mass_points für Scatter-Plot
    # TODO: Iteriere über system.springs für Linien-Plot
    
    ax.set_aspect('equal')
    ax.invert_yaxis() # Z-Achse nach unten
    st.pyplot(fig)