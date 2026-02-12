import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from mechanical_system import MechanicalSystem
from topology_optimizer import TopologyOptimizer

# --- Seitenkonfiguration ---
st.set_page_config(page_title="Topologieoptimierung", layout="wide")

st.title("Topologieoptimierung")

# --- Session State ---
if 'system' not in st.session_state:
    st.session_state['system'] = None
if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0
if 'optimizer' not in st.session_state:
    st.session_state['optimizer'] = None

# --- Sidebar: Einstellungen und Steuerung ---
st.sidebar.header("Modell-Parameter")
width = st.sidebar.number_input("Breite (Knoten)", min_value=2, value=60)
height = st.sidebar.number_input("Höhe (Knoten)", min_value=2, value=20)
target_ratio = st.sidebar.slider("Ziel-Masserate (Restmaterial)", 0.1, 1.0, 0.6)

st.sidebar.header("Visualisierung")
show_deformation = st.sidebar.checkbox("Verformung anzeigen", value=True)

# Verformungsskalierung mit Session State für feine Anpassung
# Intern speichern wir den Anzeigewert (0-10), echter Wert = Anzeige * 0.01
if 'deformation_scale_display' not in st.session_state:
    st.session_state['deformation_scale_display'] = 5.0  # 5 entspricht 0.05

col1, col2 = st.sidebar.columns(2)
if col1.button("➖ Feiner -1"):
    st.session_state['deformation_scale_display'] = max(0.0, st.session_state['deformation_scale_display'] - 1.0)
    st.rerun()
if col2.button("➕ Gröber +1"):
    st.session_state['deformation_scale_display'] = min(10.0, st.session_state['deformation_scale_display'] + 1.0)
    st.rerun()

deformation_scale_display = st.sidebar.slider("Verformungsskalierung", 0.0, 10.0, st.session_state['deformation_scale_display'])

# Slider-Wert in Session State speichern falls manuell geändert
if deformation_scale_display != st.session_state['deformation_scale_display']:
    st.session_state['deformation_scale_display'] = deformation_scale_display

# Echter Skalierungswert für die Berechnung
deformation_scale = deformation_scale_display * 0.01

st.sidebar.header("Steuerung")

if st.sidebar.button("Modell initialisieren"):
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
    st.session_state['optimizer'] = None
    st.sidebar.success("Modell erstellt!")

if st.sidebar.button("Optimieren (1 Schritt)"):
    if st.session_state['system'] is not None:
        optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
        optimizer.initial_mass = width * height 
        optimizer.run_optimization_step()
        st.session_state['optimizer'] = optimizer
        st.session_state['iteration'] += 1
        st.sidebar.success("1 Schritt durchgeführt.")
        st.rerun()
    else:
        st.sidebar.warning("Bitte erst Modell erstellen.")
        
if st.sidebar.button("Optimieren (5 Schritte)"):
    if st.session_state['system'] is not None:
        optimizer = TopologyOptimizer(st.session_state['system'], target_ratio)
        optimizer.initial_mass = width * height
        
        progress_bar = st.sidebar.progress(0)
        for i in range(5):
            optimizer.run_optimization_step()
            progress_bar.progress((i + 1) / 5)
        st.session_state['optimizer'] = optimizer
        st.session_state['iteration'] += 5
        st.sidebar.success("5 Schritte durchgeführt.")
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
            mass_before = len(st.session_state['system'].mass_points)
            optimizer.run_optimization_step()
            mass_after = len(st.session_state['system'].mass_points)
            
            # Stoppen wenn keine Knoten mehr gelöscht wurden (Zielmasse erreicht)
            if mass_before == mass_after:
                break
            
            iteration_count += 1
            st.session_state['iteration'] += 1
            
            current_mass = mass_after
            current_ratio = current_mass / initial_mass
            progress = 1.0 - (current_ratio - target_ratio) / (1.0 - target_ratio)
            progress = max(0.0, min(1.0, progress))
            
            progress_bar.progress(progress)
            status_text.text(f"Iteration {iteration_count}: {current_mass} Knoten ({current_ratio:.1%})")
        
        st.sidebar.success(f"Ziel erreicht nach {iteration_count} Iterationen!")
        st.session_state['optimizer'] = optimizer
        st.rerun()
    else:
        st.sidebar.warning("Bitte erst Modell erstellen.")

# --- Hilfsfunktion zum Plotten ---
def plot_system(system, optimizer=None, title="Struktur", show_deformation=True, deformation_scale=2.0):
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Verschiebungen abrufen, falls vorhanden
    u = None
    if optimizer is not None and optimizer.current_displacements is not None:
        u = optimizer.current_displacements
    
    # 1. Federn zeichnen (als Linien)
    for spring in system.springs:
        xa, za = spring.point_a.x, spring.point_a.z
        xb, zb = spring.point_b.x, spring.point_b.z
        
        # Verformte Position berechnen
        if u is not None and show_deformation:
            ida, idb = spring.point_a.id, spring.point_b.id
            if 2*ida+1 < len(u) and 2*idb+1 < len(u):
                xa += u[2*ida] * deformation_scale
                za += u[2*ida+1] * deformation_scale
                xb += u[2*idb] * deformation_scale
                zb += u[2*idb+1] * deformation_scale
        
        ax.plot([xa, xb], [za, zb], c='gray', linewidth=1, zorder=1)

    # 2. Knoten zeichnen (als Punkte)
    x_nodes = []
    z_nodes = []
    colors = []
    sizes = []
    
    for pid, p in system.mass_points.items():
        x, z = p.x, p.z
        
        # Verformte Position
        if u is not None and show_deformation and 2*pid+1 < len(u):
            x += u[2*pid] * deformation_scale
            z += u[2*pid+1] * deformation_scale
        
        x_nodes.append(x)
        z_nodes.append(z)
        
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
        x, z = p.x, p.z
        
        if u is not None and show_deformation and 2*pid+1 < len(u):
            x += u[2*pid] * deformation_scale
            z += u[2*pid+1] * deformation_scale
        
        ax.arrow(x, z, force[0]*0.5, force[1]*0.5, 
                 head_width=0.3, head_length=0.3, fc='orange', ec='orange', zorder=3)

    # Info-Text
    info = f"{title} - Knoten: {len(system.mass_points)}"
    if u is not None and show_deformation:
        max_disp = np.max(np.abs(u)) if len(u) > 0 else 0
        info += f" | Max. Verformung: {max_disp:.3f} (x{deformation_scale})"
    
    ax.set_title(info)
    ax.set_aspect('equal')
    ax.invert_yaxis() # Z zeigt nach unten (Mechanik-Konvention)
    ax.grid(True, alpha=0.3)
    return fig

# --- Hauptbereich (Visualisierung) ---
if st.session_state['system'] is not None:
    st.pyplot(plot_system(
        st.session_state['system'], 
        st.session_state['optimizer'],
        f"Iteration {st.session_state['iteration']}",
        show_deformation,
        deformation_scale
    ))
else:
    st.info("Noch kein Modell vorhanden. Klicke links auf 'Modell initialisieren'.")