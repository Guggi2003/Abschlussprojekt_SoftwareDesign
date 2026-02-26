import numpy as np
import pickle
from structural_components import MassPoint, LinearSpring

class MechanicalSystem:
    """
    Verwaltet das physikalische Modell: Knoten, Federn und Kräfte.
    """
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Datenspeicher (Dictionary für schnellen Zugriff per ID)
        self.mass_points: dict[int, MassPoint] = {}
        self.springs: list[LinearSpring] = []
        
        # Externe Lasten: Map {PointID: [Fx, Fz]}
        self.external_forces: dict[int, np.ndarray] = {}

    def create_initial_mesh(self):
        """
        Erstellt ein Gitter mit horizontalen, vertikalen und diagonalen Federn.
        """
        self.mass_points.clear()
        self.springs.clear()
        element_counter = 0
        
        # 1. Massenpunkte erstellen
        for z in range(self.height):
            for x in range(self.width):
                pid = z * self.width + x
                self.mass_points[pid] = MassPoint(id=pid, x=float(x), z=float(z))

        # 2. Federn erstellen
        for z in range(self.height):
            for x in range(self.width):
                p_current = self.mass_points[z * self.width + x]
                
                # Definition der Nachbarn: (dx, dz, Steifigkeitsfaktor)
                # Diagonalen sind länger (Faktor sqrt(2)), daher muss k kleiner sein (1/sqrt(2))
                neighbors = [
                    (1, 0, 1.0),                  # Rechts
                    (0, 1, 1.0),                  # Unten
                    (1, 1, 1.0 / np.sqrt(2)),     # Rechts-Unten (Kreuzverstrebung 1)
                    (-1, 1, 1.0 / np.sqrt(2))     # Links-Unten (Kreuzverstrebung 2)
                ]
                
                for dx, dz, k_factor in neighbors:
                    nx, nz = x + dx, z + dz
                    
                    # Prüfen ob Nachbar im Gitter liegt
                    if 0 <= nx < self.width and 0 <= nz < self.height:
                        p_neighbor = self.mass_points[nz * self.width + nx]
                        
                        spring = LinearSpring(element_counter, p_current, p_neighbor, stiffness=k_factor)
                        self.springs.append(spring)
                        element_counter += 1

    def assemble_global_stiffness_matrix(self) -> np.ndarray:
        """
        Baut die globale Steifigkeitsmatrix K durch Superposition auf.
        """
        if not self.mass_points:
            return np.zeros((0, 0))

        # Dimension bestimmen (höchste ID + 1) * 2 Freiheitsgrade
        max_id = max(self.mass_points.keys())
        dim = (max_id + 1) * 2
        K_global = np.zeros((dim, dim))
        
        for spring in self.springs:
            k_local = spring.calculate_local_stiffness_matrix()
            
            # Globale Indizes bestimmen: [ax, az, bx, bz]
            idx = spring.point_a.global_dof_indices + spring.point_b.global_dof_indices
            
            # In globale Matrix addieren
            # schneller als verschachtelte Schleifen
            K_global[np.ix_(idx, idx)] += k_local
            
        return K_global

    def remove_mass_point(self, point_id: int):
        """
        Löscht einen Punkt und alle verbundenen Federn.
        """
        if point_id in self.mass_points:
            del self.mass_points[point_id]
            
            if point_id in self.external_forces:
                del self.external_forces[point_id]
            
            # nur Federn behalten, die intakt sind
            self.springs = [
                s for s in self.springs 
                if s.point_a.id != point_id and s.point_b.id != point_id
            ]

    # Speichern/Laden
    def save_to_file(self, filename: str):
        """Speichert das System binär (Pickle)."""
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load_from_file(filename: str) -> 'MechanicalSystem':
        """Lädt ein gespeichertes System."""
        with open(filename, 'rb') as f:
            return pickle.load(f)