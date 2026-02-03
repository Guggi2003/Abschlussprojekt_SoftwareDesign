import numpy as np
from mechanical_system import MechanicalSystem

class TopologyOptimizationController:
    """
    Steuert den Optimierungsprozess (MVC Controller).
    """
    def __init__(self, system: MechanicalSystem, target_mass_ratio: float):
        self.system = system
        self.target_mass_ratio = target_mass_ratio
        self.initial_mass = len(system.mass_points)
        self.current_iteration = 0

    def solve_linear_system(self) -> np.ndarray:
        """
        Löst K * u = F unter Berücksichtigung der Randbedingungen.
        Entspricht der 'solve'-Funktion vom Professor.
        """
        # 1. Matrix bauen
        K = self.system.assemble_global_stiffness_matrix()
        
        # 2. Kräftevektor F bauen
        # TODO: F Vektor initialisieren und self.system.external_forces eintragen
        
        # 3. Randbedingungen anwenden (Zeilen/Spalten streichen oder 1 setzen)
        # TODO: Über self.system.mass_points iterieren und is_fixed prüfen
        
        # 4. Lösen (np.linalg.solve)
        # return displacements
        pass

    def run_optimization_step(self):
        """
        Führt EINE Iteration der Optimierung durch.
        """
        # 1. FEM Berechnung
        u = self.solve_linear_system()
        
        # 2. Wichtigkeit berechnen (Energie pro Punkt)
        importance_map = self._calculate_point_importance(u)
        
        # 3. Die unwichtigsten Punkte entfernen
        points_to_remove = self._identify_points_to_remove(importance_map)
        
        for pid in points_to_remove:
            self.system.remove_mass_point(pid)
            
        self.current_iteration += 1

    def _calculate_point_importance(self, u: np.ndarray) -> dict[int, float]:
        """Berechnet die summierte Verformungsenergie pro Punkt."""
        # TODO: Iteriere über Federn, berechne Energie, addiere auf Endpunkte
        return {}

    def _identify_points_to_remove(self, importance_map: dict[int, float]) -> list[int]:
        """Wählt die Punkte mit der geringsten Energie aus."""
        # TODO: Sortieren und untere X Prozent zurückgeben
        # WICHTIG: Prüfen, ob Lasten/Lager noch verbunden bleiben!
        return []