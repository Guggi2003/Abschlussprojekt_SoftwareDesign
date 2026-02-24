import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import glob
import pickle
import io
from mechanical_system import MechanicalSystem
from topology_optimizer import TopologyOptimizer

# --- Seitenkonfiguration ---
st.set_page_config(page_title="Topologieoptimierung", layout="wide")
st.title("Topologieoptimierung")

# --- Session State Initialisierung ---
if 'system' not in st.session_state:
    st.session_state['system'] = None
if 'iteration' not in st.session_state:
    st.session_state['iteration'] = 0
if 'optimizer' not in st.session_state:
    st.session_state['optimizer'] = None
if 'history_mass' not in st.session_state:
    st.session_state['history_mass'] = []
if 'last_displacements' not in st.session_state:
    st.session_state['last_displacements'] = None

# --- SIDEBAR (Globale Parameter & Projektverwaltung) ---
st.sidebar.header("Globale Parameter")
width = st.sidebar.number_input("Breite (Knoten)", min_value=10, value=60)
height = st.sidebar.number_input("Höhe (Knoten)", min_value=5, value=20)
target_ratio = st.sidebar.slider("Ziel-Masse (%)", min_value=0.1, max_value=1.0, value=0.35, step=0.05)

def reset_model():
    sys = MechanicalSystem(width, height)
    sys.create_initial_mesh()
    # Standard MBB-Balken Setup
    pid_left = (sys.height - 1) * sys.width
    sys.mass_points[pid_left].is_fixed_x = True
    sys.mass_points[pid_left].is_fixed_z = True
    pid_right = (sys.height - 1) * sys.width + (sys.width - 1)
    sys.mass_points[pid_right].is_fixed_x = False
    sys.mass_points[pid_right].is_fixed_z = True
    pid_top = sys.width // 2
    sys.external_forces[pid_top] = np.array([0.0, 10.0])
    
    st.session_state['system'] = sys
    st.session_state['iteration'] = 0
    st.session_state['history_mass'] = [len(sys.mass_points)]
    st.session_state['last_displacements'] = None
    st.session_state['optimizer'] = None

if st.sidebar.button("Modell zurücksetzen"):
    reset_model()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("Projektverwaltung")
save_name = st.sidebar.text_input("Dateiname", "projekt_v1")

col_save, col_load = st.sidebar.columns(2)
if col_save.button("Speichern"):
    if st.session_state['system'] is not None:
        try:
            os.makedirs("saved_models", exist_ok=True)
            save_data = {
                'system': st.session_state['system'],
                'iteration': st.session_state['iteration'],
                'history_mass': st.session_state['history_mass'],
                'history_Nachgiebigkeit': st.session_state['history_Nachgiebigkeit'],
                'last_displacements': st.session_state['last_displacements']
            }
            with open(f"saved_models/{save_name}.pkl", "wb") as f:
                pickle.dump(save_data, f)
            st.sidebar.success("Gespeichert!")
        except Exception as e:
            st.sidebar.error(f"Fehler: {e}")

saved_files = glob.glob("saved_models/*.pkl")
display_files = [os.path.basename(f) for f in saved_files]
selected_file = st.sidebar.selectbox("Gespeicherte Modelle", display_files) if display_files else None

if col_load.button("Laden"):
    if selected_file:
        try:
            with open(f"saved_models/{selected_file}", "rb") as f:
                data = pickle.load(f)
            if isinstance(data, MechanicalSystem): 
                st.session_state['system'] = data
                st.session_state['last_displacements'] = None
            else:
                st.session_state['system'] = data['system']
                st.session_state['iteration'] = data['iteration']
                st.session_state['history_mass'] = data.get('history_mass', [])
                st.session_state['last_displacements'] = data.get('last_displacements', None)
            st.session_state['optimizer'] = None
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Fehler: {e}")

if st.session_state['system'] is None:
    reset_model()

# --- SOLVER LOGIK ---
def run_opt(steps=1, auto_target=False):
    if st.session_state['system'] is None: return
    
    if st.session_state['optimizer'] is None:
        opt = TopologyOptimizer(st.session_state['system'], target_ratio)
        start_mass = st.session_state['history_mass'][0] if st.session_state['history_mass'] else (width*height)
        opt.initial_mass = start_mass
    else:
        opt = st.session_state['optimizer']
        opt.target_mass_ratio = target_ratio

    progress = st.progress(0)
    
    start_m = st.session_state['history_mass'][0] if st.session_state['history_mass'] else (width*height)
    target_m = int(start_m * target_ratio)
    
    max_iters = 1000 if auto_target else steps
    iters_done = 0
    
    for i in range(max_iters):
        curr_mass = len(st.session_state['system'].mass_points)
        
        if auto_target and curr_mass <= target_m:
            break
            
        mass_before = curr_mass
        opt.run_optimization_step()
        mass_after = len(st.session_state['system'].mass_points)
        
        st.session_state['history_mass'].append(mass_after)
        
        iters_done += 1
        
        if auto_target:
            prog_pct = 1.0 - (mass_after - target_m) / (start_m - target_m) if start_m != target_m else 1.0
            progress.progress(max(0.0, min(1.0, prog_pct)))
        else:
            progress.progress((i+1)/steps)
            
        if mass_before == mass_after:
            break
            
    progress.empty()
    st.session_state['last_displacements'] = opt.current_displacements
    st.session_state['optimizer'] = opt
    st.session_state['iteration'] += iters_done

# --- VISUALISIERUNG ---
# Neu: Parameter 'is_interactive' steuert die Klick-Events im Plot
def plot_interactive_system(system, displacements, def_scale, mode, is_interactive):
    if displacements is None and system is not None and mode == "Spannungs-Heatmap":
        temp_opt = TopologyOptimizer(system, target_ratio)
        displacements = temp_opt.solve_linear_system()
        st.session_state['last_displacements'] = displacements
        
        if not st.session_state['history_Nachgiebigkeit']:
            comp = calculate_Nachgiebigkeit(system, displacements)
            st.session_state['history_Nachgiebigkeit'].append(comp)

    node_x, node_z = [], []
    ids, colors, sizes, texts = [], [], [], []
    current_coords = {} 
    
    for pid, p in system.mass_points.items():
        x, z = p.x, p.z
        dx, dz = 0.0, 0.0
        
        if displacements is not None:
            idx = 2 * pid
            if idx+1 < len(displacements):
                dx = displacements[idx]
                dz = displacements[idx+1]

        if def_scale > 0:
            x += dx * def_scale
            z += dz * def_scale
            
        current_coords[pid] = (x, z)
        node_x.append(x)
        node_z.append(z)
        ids.append(pid)
        
        if mode == "Spannungs-Heatmap":
            mag = np.sqrt(dx**2 + dz**2)
            colors.append(mag)
            texts.append(f"ID: {pid}<br>Verformung (absolut): {mag:.5f}")
            sizes.append(9) 
        else:
            if p.is_fixed_x and p.is_fixed_z:
                colors.append('red'); sizes.append(12); texts.append("Festlager")
            elif p.is_fixed_x or p.is_fixed_z:
                colors.append('purple'); sizes.append(12); texts.append("Loslager")
            elif pid in system.external_forces:
                colors.append('orange'); sizes.append(12); texts.append("Kraft")
            else:
                colors.append('blue'); sizes.append(6); texts.append("Knoten")

    spring_x, spring_z = [], []
    for s in system.springs:
        if s.point_a.id in current_coords and s.point_b.id in current_coords:
            xa, za = current_coords[s.point_a.id]
            xb, zb = current_coords[s.point_b.id]
            spring_x.extend([xa, xb, None])
            spring_z.extend([za, zb, None])

    fig = go.Figure()

    fig.add_trace(go.Scattergl(
        x=spring_x, y=spring_z,
        mode='lines',
        line=dict(color='gray', width=1),
        hoverinfo='skip',
        name='Struktur'
    ))

    if mode == "Spannungs-Heatmap":
        cmax_val = np.percentile(colors, 95) if len(colors) > 0 else None
        marker_config = dict(
            color=colors, 
            colorscale='Turbo', 
            size=sizes,
            colorbar=dict(title="Verformung"), 
            cmin=0,
            cmax=cmax_val,
            showscale=True
        )
    else:
        marker_config = dict(color=colors, size=sizes)

    fig.add_trace(go.Scattergl(
        x=node_x, y=node_z,
        mode='markers',
        marker=marker_config,
        text=texts,
        hoverinfo='text',
        customdata=ids,
        name='Knoten'
    ))

    for pid, f in system.external_forces.items():
        if pid in current_coords:
            px, pz = current_coords[pid]
            fig.add_annotation(
                x=px, y=pz,
                ax=px - f[0]*0.2, ay=pz - f[1]*0.2,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=3, arrowcolor="orange"
            )

    # Plotly Interaktivitaet setzen
    click_mode = 'event+select' if is_interactive else 'none'
    
    fig.update_layout(
        yaxis=dict(scaleanchor="x", scaleratio=1, autorange="reversed", visible=False),
        xaxis=dict(visible=False),
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=550,
        clickmode=click_mode,
        dragmode='pan',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


# --- DASHBOARD LAYOUT ---
col_plot, col_menu = st.columns([3, 1])

view_mode = "Standard"
show_deformation = False
deformation_scale = 0.0
is_interactive = (st.session_state['iteration'] == 0)

with col_menu:
    st.write("### Steuerung")
    
    # Pre-Processing Phase (Setup)
    if st.session_state['iteration'] == 0:
        st.caption("SETUP (PRE-PROCESSING)")
        active_tool = st.radio(
            "Werkzeug wählen & im Plot anwenden:",
            [
                "Knoten inspizieren", 
                "Festlager (X/Z fixiert)", 
                "Loslager (Z fixiert)", 
                "Knotenkraft (Vektor)",
                "Randbedingung löschen"
            ]
        )
        
        force_x, force_z = 0.0, 0.0
        if "kraft" in active_tool.lower():
            st.markdown("**Kraftvektor definieren:**")
            col_fx, col_fz = st.columns(2)
            force_x = col_fx.number_input("F_x", value=0.0, step=1.0)
            force_z = col_fz.number_input("F_z", value=10.0, step=1.0)
            
        st.divider()
        st.caption("SOLVER")
        if st.button("Optimierung starten", width="stretch", type="primary"):
            run_opt(1)
            st.rerun()
            
    # Post-Processing Phase (Auswertung)
    else:
        st.caption("SOLVER")
        c1, c2 = st.columns(2)
        if c1.button("+ 1 Schritt", width="stretch"):
            run_opt(1)
            st.rerun()
        if c2.button("+ 5 Schritte", width="stretch"):
            run_opt(5)
            st.rerun()
            
        if st.button("Automatisch bis Ziel", width="stretch", type="primary"):
            run_opt(auto_target=True)
            st.rerun()
            
        st.divider()
        st.caption("ANSICHT (POST-PROCESSING)")
        view_mode = st.radio("Darstellung:", ["Standard", "Spannungs-Heatmap"], key="ui_view_mode")
        
        show_deformation = st.checkbox("Verformung anzeigen", value=False, key="ui_show_def")
        if show_deformation:
            deformation_scale = st.slider("Skalierung", min_value=0.0, max_value=0.05, value=0.025, step=0.005, format="%.3f", key="ui_def_scale")

with col_plot:
    fig = plot_interactive_system(
        st.session_state['system'], 
        st.session_state['last_displacements'], 
        deformation_scale if show_deformation else 0.0,
        view_mode,
        is_interactive
    )
    
    # Event-Listener für Klicks im Plot
    event = st.plotly_chart(fig, width="stretch", on_select="rerun")
    
    if is_interactive and event and "selection" in event:
        sel = event["selection"]
        if "points" in sel and len(sel["points"]) > 0:
            pt = sel["points"][0]
            if "customdata" in pt:
                clicked_id = pt["customdata"]
                sys = st.session_state['system']
                tool = active_tool.lower()
                
                # Vorherige Berechnungen zuruecksetzen, da sich das Setup aendert
                st.session_state['last_displacements'] = None
                
                if "festlager" in tool:
                    # Maximal ein Festlager erlaubt
                    for pid, p in sys.mass_points.items():
                        if p.is_fixed_x and p.is_fixed_z:
                            p.is_fixed_x = False
                            p.is_fixed_z = False
                    sys.mass_points[clicked_id].is_fixed_x = True
                    sys.mass_points[clicked_id].is_fixed_z = True
                    st.rerun()

                elif "loslager" in tool:
                    # Maximal ein Loslager erlaubt
                    for pid, p in sys.mass_points.items():
                        if p.is_fixed_z and not p.is_fixed_x:
                            p.is_fixed_z = False

                    sys.mass_points[clicked_id].is_fixed_x = False
                    sys.mass_points[clicked_id].is_fixed_z = True
                    st.rerun()

                    
                elif "kraft" in tool:
                    sys.external_forces[clicked_id] = np.array([force_x, force_z])
                    st.rerun()
                    
                elif "löschen" in tool:
                    sys.mass_points[clicked_id].is_fixed_x = False
                    sys.mass_points[clicked_id].is_fixed_z = False
                    if clicked_id in sys.external_forces:
                        del sys.external_forces[clicked_id]
                    st.rerun()

st.divider()
st.subheader("Analyse & Konvergenz")

current_mass = len(st.session_state['system'].mass_points)
start_mass = st.session_state['history_mass'][0] if st.session_state['history_mass'] else (width*height)
target_mass = int(start_mass * target_ratio)

col_met1, col_met2, col_met3 = st.columns(3)
col_met1.metric("Iteration", st.session_state['iteration'])
col_met2.metric("Aktuelle Masse (Knoten)", current_mass)
col_met3.metric("Ziel Masse (Knoten)", target_mass)

if st.session_state['history_mass']:
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**Masse-Verlauf (Knotenanzahl)**")
        st.line_chart(st.session_state['history_mass'], height=250)
    with col_chart2:
        st.markdown("**Nachgiebigkeit-Verlauf**")
        if st.session_state['history_Nachgiebigkeit']:
            st.line_chart(st.session_state['history_Nachgiebigkeit'], height=250)

with col_menu:
    if st.session_state['iteration'] > 0:
        st.divider()
        st.caption("EXPORT")
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=600, scale=2)
            st.download_button(
                label="Bild exportieren (.png)",
                data=img_bytes,
                file_name=f"struktur_iter_{st.session_state['iteration']}.png",
                mime="image/png",
                width="stretch"
            )
        except Exception:
            st.warning("⚠️ 'kaleido' fehlt für Bild-Export.")
