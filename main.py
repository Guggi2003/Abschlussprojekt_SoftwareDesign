import streamlit as st
import matplotlib.pyplot as plt
from enum import Enum, auto

class AppState(Enum):
    INIT = auto()
    GEOMETRY = auto()
    CONNECTIONS = auto()
    BC = auto()
    LOADS = auto()
    REVIEW = auto()
    SOLVE = auto()
    OPTIMIZE = auto()
    RESULTS = auto()
    ERROR = auto()

def goto(state: AppState | str):
    if isinstance(state, AppState):
        st.session_state.state = state.name
    else:
        st.session_state.state = state

def set_error(msg: str, back: AppState):
    st.session_state.error_msg = msg
    st.session_state.error_back = back.name
    st.session_state.state = AppState.ERROR.name

def init_session():
    if "state" not in st.session_state:
        st.session_state.state = AppState.INIT.name
    if "model" not in st.session_state:
        st.session_state.model = None
    if "error_msg" not in st.session_state:
        st.session_state.error_msg = ""
    if "error_back" not in st.session_state:
        st.session_state.error_back = AppState.GEOMETRY.name

def page_init():
    # Defaults (only once)
    if st.session_state.model is None:
        st.session_state.model = {
            "nx": 10, "ny": 6, "nz": 1, "dx": 1.0,
            "springs": {"axial": 1.0, "diag": 1.0, "enabled": {"axial": True, "diag": True}},
            "bcs": [],      # list of {"node": id, "fix": (fx,fy,fz)}
            "loads": [],    # list of {"F": (Fx,Fy,Fz), "x": float, "y": float, "z": float}
            "dim": 3,
        }
    st.title("Gib die Werte in den Solver ein")
    st.write("Welcome to the FEM Solver application.")
    if st.button("Start"):
        goto(AppState.LOADS)
        st.rerun()

def page_geometry():
    m = st.session_state.model
    st.header("Geometry")
    dim = st.selectbox("Dimension", [2, 3], index=0 if m["dim"] == 2 else 1)
    nx = st.number_input("nx", min_value=2, value=int(m["nx"]))
    ny = st.number_input("ny", min_value=2, value=int(m["ny"]))
    nz = 1
    if dim == 3:
        nz = st.number_input("nz", min_value=2, value=max(2, int(m["nz"])))
    dx = st.number_input("dx", min_value=1e-6, value=float(m["dx"]))

    col1, col2 = st.columns(2)
    if col1.button("Next"):
        if dx <= 0 or nx < 2 or ny < 2 or (dim == 3 and nz < 2):
            set_error("Invalid geometry parameters.", AppState.GEOMETRY)
            return
        m.update({"dim": dim, "nx": nx, "ny": ny, "nz": nz, "dx": dx})
        goto(AppState.CONNECTIONS)
    if col2.button("Reset"):
        goto(AppState.INIT)

def page_connections():
    m = st.session_state.model
    st.header("Springs")
    axial_on = st.checkbox("Enable axial springs", value=m["springs"]["enabled"]["axial"])
    diag_on = st.checkbox("Enable diagonal springs", value=m["springs"]["enabled"]["diag"])
    k_ax = st.number_input("k_axial", min_value=0.0, value=float(m["springs"]["axial"]))
    k_d  = st.number_input("k_diag",  min_value=0.0, value=float(m["springs"]["diag"]))

    col1, col2 = st.columns(2)
    if col1.button("Back"):
        goto(AppState.GEOMETRY)
    if col2.button("Next"):
        if (not axial_on and not diag_on) or (axial_on and k_ax == 0.0 and (not diag_on or k_d == 0.0)):
            set_error("No effective stiffness selected.", AppState.CONNECTIONS)
            return
        m["springs"]["enabled"].update({"axial": axial_on, "diag": diag_on})
        m["springs"].update({"axial": k_ax, "diag": k_d})
        goto(AppState.BC)

def page_bc():
    m = st.session_state.model
    st.header("Boundary conditions")
    # node selection: you will map (i,j,k) -> node_id in your MechanicalSystem
    node = st.number_input("Node id", min_value=0, value=0, step=1)
    fx = st.checkbox("fix x", value=True)
    fy = st.checkbox("fix y", value=False if m["dim"] == 2 else True)
    fz = st.checkbox("fix z", value=True if m["dim"] == 2 else False)

    col1, col2, col3 = st.columns(3)
    if col1.button("Add BC"):
        m["bcs"].append({"node": int(node), "fix": (fx, fy, fz)})
    if col2.button("Back"):
        goto(AppState.CONNECTIONS)
    if col3.button("Next"):
        if len(m["bcs"]) == 0:
            set_error("At least one support required.", AppState.BC)
            return
        goto(AppState.LOADS)

    st.write("Current BCs:", m["bcs"])

def page_loads():
    m = st.session_state.model
    st.header("Loads")
    st.subheader("Point (x/y/z)")
    x = st.number_input("x", value=0.0)
    y = st.number_input("y", value=0.0)
    z = st.number_input("z", value=0.0)
    Fx = st.number_input("Fx", value=0.0)
    Fy = st.number_input("Fy", value=0.0)
    Fz = st.number_input("Fz", value=0.0)

    if st.button("Visualize"):
        m["loads"] = [{"x": float(x), "y": float(y), "z": float(z), "F": (Fx, Fy, Fz)}]
        goto(AppState.RESULTS)
        st.rerun()

def page_review():
    m = st.session_state.model
    st.header("Review")
    st.json(m)

    col1, col2, col3 = st.columns(3)
    if col1.button("Back"):
        goto(AppState.LOADS)
    if col2.button("Solve"):
        goto(AppState.SOLVE)
    if col3.button("Optimize"):
        goto(AppState.OPTIMIZE)

def page_solve():
    st.header("Solve")
    # Here: build MechanicalSystem from m, assemble, solve
    # u = system.solve()
    # if u is None: set_error(...)
    st.success("Stub: solved.")
    if st.button("Next"):
        goto(AppState.RESULTS)

def page_optimize():
    st.header("Optimize")
    # Here: run optimizer iterations (prefer step-wise button to avoid long run)
    # store history
    st.success("Stub: optimized.")
    if st.button("Next"):
        goto(AppState.RESULTS)

def page_results():
    st.header("Results")
    if st.button("Start over"):
        goto(AppState.INIT)
        st.rerun()

def page_error():
    st.error(st.session_state.error_msg)
    if st.button("Back"):
        goto(st.session_state.error_back)

PAGES = {
    AppState.INIT.name: page_init,
    AppState.GEOMETRY.name: page_geometry,
    AppState.CONNECTIONS.name: page_connections,
    AppState.BC.name: page_bc,
    AppState.LOADS.name: page_loads,
    AppState.REVIEW.name: page_review,
    AppState.SOLVE.name: page_solve,
    AppState.OPTIMIZE.name: page_optimize,
    AppState.RESULTS.name: page_results,
    AppState.ERROR.name: page_error,
}

def main():
    init_session()
    page = PAGES.get(st.session_state.state)
    if page is None:
        st.session_state.state = AppState.INIT.name
        page = PAGES[AppState.INIT.name]
    page()

if __name__ == "__main__":
    main()
