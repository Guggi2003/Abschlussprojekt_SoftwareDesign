import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mechanical_system import MechanicalSystem
from topology_optimizer import TopologyOptimizer

# --- Seitenkonfiguration ---
st.set_page_config(page_title="Topologieoptimierung", layout="wide")

st.title("Topologieoptimierung von 2D-Strukturen")

# --- Sidebar: Einstellungen ---
st.sidebar.header("Modell-Parameter")
width = st.sidebar.number_input("Breite (Knoten)", min_value=2, value=12)
height = st.sidebar.number_input("Höhe (Knoten)", min_value=2, value=4)
target_ratio = st.sidebar.slider("Ziel-Masserate (Restmaterial)", 0.1, 1.0, 0.4)

# --- Session State ---
if 'system' not in st.session_state:
    st.session_state['system'] = None
if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0

# --- Hilfsfunktion zum Plotten ---
def plot_system(system, title="Struktur"):
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # 1. Federn zeichnen (als Linien)
    for spring in system.springs:
        x_values = [spring.point_a.x, spring.point_b.x]
        z_values = [spring.point_a.z, spring.point_b.z]
        # Grau, dünn
        ax.plot(x_values, z_values, c='gray', linewidth=1, zorder=1)

    # 2. Knoten zeichnen (als Punkte)
    x_nodes = []
    z_nodes = []
    colors = []
    sizes = []
    
    for pid, p in system.mass_points.items():
        x_nodes.append(p.x)
        z_nodes.append(p.z)
        
        # Farbe basierend auf Status
        if p.is_fixed_x or p.is_fixed_z:
            colors.append('red') # Lager = Rot
            sizes.append(50)
        elif pid in system.external_forces:
            colors.append('orange') # Kraft = Orange
            sizes.append(50)
        else:
            colors.append('blue') # Normal = Blau
            sizes.append(15)

    ax.scatter(x_nodes, z_nodes, c=colors, s=sizes, zorder=2)
    
    # 3. Kräfte als Pfeile einzeichnen
    for pid, force in system.external_forces.items():
        p = system.mass_points[pid]
        # Pfeil zeichnen (skaliert)
        ax.arrow(p.x, p.z, force[0]*0.5, force[1]*0.5, 
                 head_width=0.3, head_length=0.3, fc='orange', ec='orange', zorder=3)

    ax.set_title(f"{title} - Punkte: {len(system.mass_points)}")
    ax.set_aspect('equal')
    ax.invert_yaxis() # Z zeigt nach unten (Mechanik-Konvention)
    ax.grid(True, alpha=0.3)
    return fig

# --- Hauptbereich ---
col_ctrl, col_view = st.columns([1, 3])

with col_ctrl:
    st.subheader("Steuerung")
    
    if st.button("1. Modell initialisieren (MBB Balken)"):
        # System erstellen
        sys = MechanicalSystem(width, height)
        sys.create_initial_mesh()
        
        # --- SZENARIO: MBB Balken (Brücke) ---
        # "Eine Seite Festlager, eine Seite Loslager, Kraft oben mittig"
        
        # 1. Festlager (Links unten)
        # Koordinaten: x=0, z=height-1 (unten)
        pid_left = (sys.height - 1) * sys.width + 0
        if pid_left in sys.mass_points:
            sys.mass_points[pid_left].is_fixed_x = True # Bewegung in X gesperrt
            sys.mass_points[pid_left].is_fixed_z = True # Bewegung in Z gesperrt
            
        # 2. Loslager (Rechts unten)
        # Koordinaten: x=width-1, z=height-1 (unten)
        pid_right = (sys.height - 1) * sys.width + (sys.width - 1)
        if pid_right in sys.mass_points:
            sys.mass_points[pid_right].is_fixed_x = False # ROLLENLAGER: X darf sich bewegen!
            sys.mass_points[pid_right].is_fixed_z = True  # Z ist gesperrt (Auflager)

        # 3. Kraft (Oben mittig)
        # Koordinaten: x=mitte, z=0 (oben)
        mid_x = sys.width // 2
        pid_force = 0 * sys.width + mid_x
        
        if pid_force in sys.mass_points:
            # Kraftvektor nach unten (Fz = 10.0)
            # Fx = 0
            sys.external_forces[pid_force] = np.array([0.0, 10.0]) 
            
        st.session_state['system'] = sys
        st.session_state['iteration'] = 0
        st.success("MBB-Modell erstellt: Lager unten, Kraft oben mittig.")

    if st.button("2. Einzelschritt optimieren"):
        if st.session_state['system'] is not None:
            optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
            # optimizer.initial_mass muss korrekt gesetzt sein, wir hacken es kurz rein, 
            # falls wir iterativ optimieren (damit er nicht jedes mal resettet)
            # In einer echten App würde man den Optimizer im SessionState halten.
            # Hier initialisieren wir ihn neu, aber setzen die Zielgröße basierend auf Originalgröße (grob)
            optimizer.initial_mass = width * height 
            
            optimizer.run_optimization_step()
            st.session_state['iteration'] += 1
        else:
            st.warning("Bitte erst Modell erstellen.")
            
    if st.button("Automatischer Loop (5 Schritte)"):
        if st.session_state['system'] is not None:
            optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
            optimizer.initial_mass = width * height
            
            progress_bar = st.progress(0)
            for i in range(5):
                optimizer.run_optimization_step()
                progress_bar.progress((i + 1) / 5)
            st.session_state['iteration'] += 5
            st.success("5 Iterationen durchgeführt.")

with col_view:
    if st.session_state['system'] is not None:
        st.pyplot(plot_system(st.session_state['system'], f"Iteration {st.session_state['iteration']}"))
    else:
        st.info("Noch kein Modell vorhanden. Klicke links auf 'Modell initialisieren'.")