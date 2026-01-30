import numpy as np
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class MassPoint:
    """
    Repräsentiert einen Knoten (Massenpunkt) im Graphen.
    """
    id: int
    x: float
    z: float
    is_fixed_x: bool = False
    is_fixed_z: bool = False
    
    # Optional: Speichert, welche Federn an diesem Punkt hängen (für Graph-Traversierung)
    connected_element_ids: list[int] = field(default_factory=list)

    @property
    def global_dof_indices(self) -> list[int]:
        """Gibt die Indizes [u_x, u_z] für die globale Matrix zurück."""
        return [2 * self.id, 2 * self.id + 1]

class StructuralElement(ABC):
    """
    Abstrakte Basisklasse für alle Elemente (z.B. Federn).
    Definiert das Interface, das alle Elemente erfüllen müssen.
    """
    def __init__(self, element_id: int, point_a: MassPoint, point_b: MassPoint):
        self.element_id = element_id
        self.point_a = point_a
        self.point_b = point_b

    @abstractmethod
    def calculate_local_stiffness_matrix(self) -> np.ndarray:
        """Muss eine 4x4 Matrix (für 2D) zurückgeben."""
        pass

    @abstractmethod
    def calculate_strain_energy(self, global_displacements: np.ndarray) -> float:
        """Berechnet die Energie basierend auf den aktuellen Verschiebungen."""
        pass

class LinearSpring(StructuralElement):
    """
    Konkrete Implementierung einer linearen Feder.
    """
    def __init__(self, element_id: int, point_a: MassPoint, point_b: MassPoint, stiffness: float = 1.0):
        super().__init__(element_id, point_a, point_b)
        self.stiffness = stiffness

    def calculate_local_stiffness_matrix(self) -> np.ndarray:
        # TODO: Implementiere hier die Logik aus solver.py (Rotationsmatrix & Kronecker)
        # return np.zeros((4, 4))
        pass

    def calculate_strain_energy(self, global_displacements: np.ndarray) -> float:
        # TODO: Implementiere c = 0.5 * u.T * K * u
        # return 0.0
        pass