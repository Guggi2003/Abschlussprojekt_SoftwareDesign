import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mechanical_system import MechanicalSystem
from topology_optimizer import TopologyOptimizer

# --- Seitenkonfiguration ---
st.set_page_config(page_title="Topologieoptimierung", layout="wide")

st.title("Topologieoptimierung von 2D-Strukturen")

# --- Session State ---
if 'system' not in st.session_state:
    st.session_state['system'] = None
if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0

# --- Sidebar: Einstellungen und Steuerung ---
st.sidebar.header("Modell-Parameter")
width = st.sidebar.number_input("Breite (Knoten)", min_value=2, value=12)
height = st.sidebar.number_input("Höhe (Knoten)", min_value=2, value=4)
target_ratio = st.sidebar.slider("Ziel-Masserate (Restmaterial)", 0.1, 1.0, 0.4)

st.sidebar.header("Steuerung")

if st.sidebar.button("1. Modell initialisieren (MBB Balken)"):
    # System erstellen
    sys = MechanicalSystem(width, height)
    sys.create_initial_mesh()
    
    # --- SZENARIO: MBB Balken (Brücke) ---
    # 1. Festlager (Links unten)
    pid_left = (sys.height - 1) * sys.width + 0
    if pid_left in sys.mass_points:
        sys.mass_points[pid_left].is_fixed_x = True
        sys.mass_points[pid_left].is_fixed_z = True
        
    # 2. Loslager (Rechts unten)
    pid_right = (sys.height - 1) * sys.width + (sys.width - 1)
    if pid_right in sys.mass_points:
        sys.mass_points[pid_right].is_fixed_x = False
        sys.mass_points[pid_right].is_fixed_z = True

    # 3. Kraft (Oben mittig)
    mid_x = sys.width // 2
    pid_force = 0 * sys.width + mid_x
    
    if pid_force in sys.mass_points:
        sys.external_forces[pid_force] = np.array([0.0, 10.0]) 
        
    st.session_state['system'] = sys
    st.session_state['iteration'] = 0
    st.sidebar.success("MBB-Modell erstellt!")

if st.sidebar.button("2. Einzelschritt optimieren"):
    if st.session_state['system'] is not None:
        optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
        optimizer.initial_mass = width * height 
        optimizer.run_optimization_step()
        st.session_state['iteration'] += 1
        st.rerun()
    else:
        st.sidebar.warning("Bitte erst Modell erstellen.")
        
if st.sidebar.button("Automatischer Loop (5 Schritte)"):
    if st.session_state['system'] is not None:
        optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
        optimizer.initial_mass = width * height
        
        progress_bar = st.sidebar.progress(0)
        for i in range(5):
            optimizer.run_optimization_step()
            progress_bar.progress((i + 1) / 5)
        st.session_state['iteration'] += 5
        st.sidebar.success("5 Iterationen durchgeführt.")
        st.rerun()

if st.sidebar.button("Optimieren bis Ziel erreicht"):
    if st.session_state['system'] is not None:
        optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
        optimizer.initial_mass = width * height
        initial_mass = len(st.session_state['system'].mass_points)
        target_mass = int(initial_mass * target_ratio)
        
        max_iterations = 1000
        iteration_count = 0
        
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        while len(st.session_state['system'].mass_points) > target_mass and iteration_count < max_iterations:
            optimizer.run_optimization_step()
            iteration_count += 1
            st.session_state['iteration'] += 1
            
            current_mass = len(st.session_state['system'].mass_points)
            current_ratio = current_mass / initial_mass
            progress = 1.0 - (current_ratio - target_ratio) / (1.0 - target_ratio)
            progress = max(0.0, min(1.0, progress))
            
            progress_bar.progress(progress)
            status_text.text(f"Iteration {iteration_count}: {current_mass} Knoten ({current_ratio:.1%})")
        
        st.sidebar.success(f"Ziel erreicht nach {iteration_count} Iterationen!")
        st.rerun()
    else:
        st.sidebar.warning("Bitte erst Modell erstellen.")

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

# --- Hauptbereich (Visualisierung) ---
if st.session_state['system'] is not None:
    st.pyplot(plot_system(st.session_state['system'], f"Iteration {st.session_state['iteration']}"))
else:
        st.info("Noch kein Modell vorhanden. Klicke links auf 'Modell initialisieren'.")