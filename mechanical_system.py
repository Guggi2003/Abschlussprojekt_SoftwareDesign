import numpy as np
import pickle
from structural_components import MassPoint, LinearSpring

class MechanicalSystem:
    """
    Verwaltet den Graphen aus Massenpunkten und Federn.
    """
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Datenspeicher (Der Graph)
        self.mass_points: dict[int, MassPoint] = {}
        self.springs: list[LinearSpring] = []
        
        # Lasten: Key = PointID, Value = [Fx, Fz]
        self.external_forces: dict[int, np.ndarray] = {}

    def create_initial_mesh(self):
        """
        Erstellt das initiale Rechteck-Gitter aus Punkten und Federn.
        """
        # TODO: Doppelte Schleife über width und height
        # TODO: MassPoints erstellen
        # TODO: Federn (horizontal, vertikal, diagonal) erstellen
        pass

    def assemble_global_stiffness_matrix(self) -> np.ndarray:
        """
        Erstellt die große K_g Matrix durch Superposition aller Federn.
        """
        n_dof = len(self.mass_points) * 2
        K_global = np.zeros((n_dof, n_dof))
        
        # TODO: Iteriere über self.springs
        # TODO: Hole lokale Matrix
        # TODO: Addiere auf K_global an den richtigen Indizes
        
        return K_global

    def remove_mass_point(self, point_id: int):
        """
        Entfernt einen Punkt und alle daran hängenden Federn aus dem System.
        """
        # TODO: Punkt aus self.mass_points löschen
        # TODO: Alle Federn aus self.springs löschen, die diesen Punkt nutzen
        pass

    def save_to_file(self, filename: str):
        """Speichert das System (Pickle)."""
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load_from_file(filename: str) -> 'MechanicalSystem':
        """Lädt das System."""
        with open(filename, 'rb') as f:
            return pickle.load(f)