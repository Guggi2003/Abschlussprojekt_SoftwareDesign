import numpy as np
from mechanical_system import MechanicalSystem

class TopologyOptimizer:
    """
    Steuert den Optimierungsprozess (MVC Controller).
    Verbindet das mechanische System mit der Optimierungslogik.
    """
    def __init__(self, system: MechanicalSystem, target_mass_ratio: float):
        self.system = system
        self.target_mass_ratio = target_mass_ratio
        
        # Startmasse merken für Abbruchkriterium
        self.initial_mass = len(system.mass_points)
        self.current_iteration = 0
        
        # History-Speicher für Dämpfung (verhindert Oszillieren der Lösung)
        self.previous_energies: dict[int, float] = {}

    def solve_linear_system(self) -> np.ndarray:
        """
        Löst das lineare Gleichungssystem K * u = F.
        
        Besonderheit:
        Behandelt automatisch 'Geister-Knoten' (Knoten, die gelöscht wurden),
        indem Null-Zeilen in der Matrix erkannt und fixiert werden.
        """
        # 1. Globale Steifigkeitsmatrix bauen
        K = self.system.assemble_global_stiffness_matrix()
        n_dof = K.shape[0]
        
        # Sicherheits-Check: Falls alles gelöscht wurde
        if n_dof == 0:
            return np.array([])

        F = np.zeros(n_dof)
        
        # 2. Kräfte eintragen
        for pid, force in self.system.external_forces.items():
            if pid in self.system.mass_points:
                idx = 2 * pid
                # Kraftkomponenten addieren
                if idx < n_dof: F[idx] += force[0]
                if idx + 1 < n_dof: F[idx + 1] += force[1]

        # 3. Randbedingungen (Lager) identifizieren
        fixed_indices = []
        for pid, p in self.system.mass_points.items():
            if p.is_fixed_x: fixed_indices.append(2 * pid)
            if p.is_fixed_z: fixed_indices.append(2 * pid + 1)

        # 4. "Ghost-Nodes" fixieren (WICHTIG!)
        # Wir suchen Zeilen, die komplett 0 sind (gelöschte Punkte).
        # Diese machen die Matrix singulär. Wir behandeln sie wie Lager.
        row_sums = np.sum(np.abs(K), axis=1)
        zero_rows = np.where(row_sums < 1e-10)[0]
        
        # Lager und Geister-Knoten zusammenführen
        all_fixed_indices = set(fixed_indices).union(set(zero_rows))
        
        # 5. Randbedingungen anwenden (Dirichlet)
        # Zeile/Spalte nullen, Diagonale auf 1 setzen -> Zwangsbewegung 0
        for d in all_fixed_indices:
            if d < n_dof:
                K[d, :] = 0.0
                K[:, d] = 0.0
                K[d, d] = 1.0
                F[d] = 0.0

        # 6. Lösen mit Fallback
        try:
            return np.linalg.solve(K, F)
        except np.linalg.LinAlgError:
            print("Warnung: Matrix singulär trotz Fix. Regularisierung...")
            # Letzter Rettungsanker: Addiere kleine Werte auf die GESAMTE Diagonale
            return np.linalg.solve(K + np.eye(n_dof) * 1e-6, F)

    def run_optimization_step(self):
        """
        Führt EINE Iteration der Optimierung durch.
        Ablauf: FEM -> Wichtigkeit berechnen -> Filtern -> Löschen.
        """
        # Abbruch prüfen
        target_count = int(self.initial_mass * self.target_mass_ratio)
        if len(self.system.mass_points) <= target_count:
            print("Zielmasse erreicht.")
            return

        # 1. FEM Berechnung (Verschiebungen u)
        u = self.solve_linear_system()
        
        # 2. Wichtigkeit berechnen (Strain Energy + Filter + Dämpfung)
        importance_map = self._calculate_point_importance(u)
        
        # 3. Die unwichtigsten Punkte identifizieren (mit Konnektivitäts-Check)
        points_to_remove = self._identify_points_to_remove(importance_map)
        
        # 4. Löschen
        for pid in points_to_remove:
            self.system.remove_mass_point(pid)
            
        self.current_iteration += 1
        print(f"Iteration {self.current_iteration}: {len(points_to_remove)} Punkte entfernt.")

    def _calculate_point_importance(self, u: np.ndarray) -> dict[int, float]:
        """
        Berechnet die 'Wichtigkeit' jedes Punktes.
        Optimiert für dickere Balkenstrukturen.
        """
        # A) Rohe Energie aus den Federn berechnen
        current_energies = {pid: 0.0 for pid in self.system.mass_points}
        
        for spring in self.system.springs:
            energy = spring.calculate_strain_energy(u)
            if spring.point_a.id in current_energies:
                current_energies[spring.point_a.id] += 0.5 * energy
            if spring.point_b.id in current_energies:
                current_energies[spring.point_b.id] += 0.5 * energy

        # B) Dämpfung (History Averaging) - WICHTIG für Stabilität
        merged_energies = {}
        for pid, energy in current_energies.items():
            prev = self.previous_energies.get(pid, energy)
            merged_energies[pid] = (energy + prev) / 2.0
        
        self.previous_energies = merged_energies

        # C) Sensitivity Filter (Optimiert für dicke Balken)
        filtered_energies = {}
        # ERHÖHT: Radius 4.0 sorgt für breitere Strukturen bei 60x20 Gitter
        r_min = 4.0  
        
        active_points = list(self.system.mass_points.values())
        
        for p_i in active_points:
            weighted_energy_sum = 0.0
            weight_sum = 0.0
            
            for p_j in active_points:
                # Bounding Box Check
                if abs(p_i.x - p_j.x) > r_min or abs(p_i.z - p_j.z) > r_min:
                    continue

                dist = np.sqrt((p_i.x - p_j.x)**2 + (p_i.z - p_j.z)**2)
                
                if dist < r_min:
                    # Quadratische Gewichtung statt linear
                    # Das fokussiert die Energie stärker auf den Kern der Balken
                    weight = (r_min - dist)**2 
                    
                    weighted_energy_sum += weight * merged_energies[p_j.id]
                    weight_sum += weight
            
            if weight_sum > 0:
                filtered_energies[p_i.id] = weighted_energy_sum / weight_sum
            else:
                filtered_energies[p_i.id] = merged_energies[p_i.id]
                
        return filtered_energies

    def _identify_points_to_remove(self, importance_map: dict[int, float]) -> list[int]:
        """
        Wählt Punkte zum Entfernen aus.
        Nutzt Breitensuche (BFS), um sicherzustellen, dass das System nicht auseinanderfällt.
        """
        # 1. Kritische Punkte identifizieren (Lager & Lasten)
        critical_points = []
        for pid, p in self.system.mass_points.items():
            # Lager?
            if p.is_fixed_x or p.is_fixed_z:
                critical_points.append(pid)
            # Last?
            elif pid in self.system.external_forces:
                critical_points.append(pid)
        
        # 2. Kandidaten sortieren (Geringste Energie zuerst)
        candidates = sorted(importance_map.items(), key=lambda x: x[1])
        
        # 3. Limit bestimmen (Evolutionary Rate)
        # Wir löschen nur ca. 1% der aktuellen Punkte pro Schritt -> Stabilität
        current_total = len(self.system.mass_points)
        target_total = int(self.initial_mass * self.target_mass_ratio)
        max_removable = current_total - target_total
        
        if max_removable <= 0:
            return []
            
        desired_removal = int(current_total * 0.01)
        limit = max(1, min(desired_removal, max_removable))
        
        points_to_remove = []
        
        # Set der IDs für die Simulation kopieren
        active_ids = set(self.system.mass_points.keys())
        
        for pid, _ in candidates:
            if len(points_to_remove) >= limit:
                break
            
            # Kritische Punkte dürfen nie gelöscht werden
            if pid in critical_points:
                continue
            
            # SIMULATION: Punkt temporär entfernen
            active_ids.remove(pid)
            
            # CHECK: Ist die Struktur noch verbunden?
            if self._is_structure_connected(active_ids, critical_points):
                # Ja -> Punkt darf gelöscht werden
                points_to_remove.append(pid)
            else:
                # Nein -> Punkt ist eine Brücke! Wieder reintun.
                active_ids.add(pid)
        
        return points_to_remove

    def _is_structure_connected(self, active_point_ids: set, critical_points: list[int]) -> bool:
        """
        Prüft mittels Breitensuche (BFS), ob alle kritischen Punkte
        noch miteinander verbunden sind.
        """
        if not critical_points:
            return True
            
        # 1. Adjazenzliste bauen (nur für aktive Punkte)
        adj = {pid: [] for pid in active_point_ids}
        
        for spring in self.system.springs:
            ida = spring.point_a.id
            idb = spring.point_b.id
            
            # Nur Federn betrachten, deren beide Enden noch existieren
            if ida in active_point_ids and idb in active_point_ids:
                adj[ida].append(idb)
                adj[idb].append(ida)
        
        # 2. Startpunkt für die Suche
        start_node = critical_points[0]
        if start_node not in adj:
            return False 
            
        # 3. BFS Algorithmus
        visited = {start_node}
        queue = [start_node]
        
        while queue:
            current = queue.pop(0)
            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        # 4. Prüfen, ob alle kritischen Punkte erreicht wurden
        return all(cp in visited for cp in critical_points)