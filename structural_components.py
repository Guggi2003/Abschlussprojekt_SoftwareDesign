import numpy as np
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class MassPoint:
    """
    Repräsentiert einen einzelnen Massenpunkt (Knoten) im Gitter.
    """
    id: int
    x: float
    z: float
    is_fixed_x: bool = False  # Festlager in X-Richtung (Verschiebung gesperrt)
    is_fixed_z: bool = False  # Festlager in Z-Richtung (Verschiebung gesperrt)

    @property
    def global_dof_indices(self) -> list[int]:
        """
        Gibt die globalen Indizes [u_x, u_z] für das Gleichungssystem zurück.
        Jeder Knoten hat 2 Freiheitsgrade.
        """
        return [2 * self.id, 2 * self.id + 1]

class StructuralElement(ABC):
    """
    Abstrakte Basisklasse für alle Elemente (z.B. Federn).
    Definiert das Interface für die Berechnung von Steifigkeit und Energie.
    """
    def __init__(self, element_id: int, point_a: MassPoint, point_b: MassPoint):
        self.element_id = element_id
        self.point_a = point_a
        self.point_b = point_b

    @abstractmethod
    def calculate_local_stiffness_matrix(self) -> np.ndarray:
        """Berechnet die lokale Steifigkeitsmatrix im globalen Koordinatensystem."""
        pass

    @abstractmethod
    def calculate_strain_energy(self, global_displacements: np.ndarray) -> float:
        """Berechnet die Verformungsenergie basierend auf den globalen Verschiebungen."""
        pass

class LinearSpring(StructuralElement):
    """
    Eine lineare Feder zwischen zwei Punkten.
    Implementiert die lokale Steifigkeitsmatrix inkl. Rotation im 2D-Raum.
    """
    def __init__(self, element_id: int, point_a: MassPoint, point_b: MassPoint, stiffness: float = 1.0):
        super().__init__(element_id, point_a, point_b)
        self.stiffness = stiffness

    def calculate_local_stiffness_matrix(self) -> np.ndarray:
        # 1. Geometrie: Vektor und Länge berechnen
        dx = self.point_b.x - self.point_a.x
        dz = self.point_b.z - self.point_a.z
        length = np.sqrt(dx**2 + dz**2)
        
        # Schutz vor Division durch Null
        if length == 0:
            return np.zeros((4, 4))

        # 2. Richtungsvektor (Einheitsvektor e_n)
        e_n = np.array([dx, dz]) / length
        
        # 3. Transformationsmatrix O = e_n * e_n^T (Tensorprodukt)
        transformation_matrix = np.outer(e_n, e_n)
        
        # 4. Basis-Steifigkeit k * [1 -1; -1 1]
        k_base = self.stiffness * np.array([[1.0, -1.0], 
                                            [-1.0, 1.0]])
        
        # 5. Kronecker-Produkt zur Erweiterung auf 4x4 (u_ax, u_az, u_bx, u_bz)
        k_local = np.kron(k_base, transformation_matrix)
        
        return k_local

    def calculate_strain_energy(self, global_displacements: np.ndarray) -> float:
        # Indizes der beteiligten Freiheitsgrade: [u_ax, u_az, u_bx, u_bz]
        indices = self.point_a.global_dof_indices + self.point_b.global_dof_indices
        
        # Verschiebungen für dieses Element holen
        u_element = global_displacements[indices]
        k_element = self.calculate_local_stiffness_matrix()
        
        # Energieformel: E = 0.5 * u^T * K * u
        energy = 0.5 * (u_element.T @ k_element @ u_element)
        
        return float(energy)