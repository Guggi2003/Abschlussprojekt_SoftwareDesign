import numpy as np
from mechanical_system import MechanicalSystem

class TopologyOptimizer:
    """
    Steuert den Optimierungsprozess.
    """
    def __init__(self, system: MechanicalSystem, target_mass_ratio: float):
        self.system = system
        self.target_mass_ratio = target_mass_ratio
        
        self.initial_mass = len(system.mass_points)
        self.current_iteration = 0
        self.previous_energies: dict[int, float] = {}
        
        #Speichern die Verschiebungen für den Plot
        self.current_displacements: np.ndarray = None

    def solve_linear_system(self) -> np.ndarray:
        """Löst K * u = F robust."""
        K = self.system.assemble_global_stiffness_matrix()
        n_dof = K.shape[0]
        if n_dof == 0: return np.array([])
        F = np.zeros(n_dof)
        
        for pid, force in self.system.external_forces.items():
            if pid in self.system.mass_points:
                idx = 2 * pid
                if idx < n_dof: F[idx] += force[0]
                if idx + 1 < n_dof: F[idx + 1] += force[1]

        fixed_indices = []
        for pid, p in self.system.mass_points.items():
            if p.is_fixed_x: fixed_indices.append(2 * pid)
            if p.is_fixed_z: fixed_indices.append(2 * pid + 1)

        row_sums = np.sum(np.abs(K), axis=1)
        zero_rows = np.where(row_sums < 1e-10)[0]
        all_fixed = set(fixed_indices).union(set(zero_rows))
        
        for d in all_fixed:
            if d < n_dof:
                K[d,:]=0; K[:,d]=0; K[d,d]=1; F[d]=0

        try:
            return np.linalg.solve(K, F)
        except np.linalg.LinAlgError:
            return np.linalg.solve(K + np.eye(n_dof)*1e-6, F)

    def run_optimization_step(self):
        target_count = int(self.initial_mass * self.target_mass_ratio)
        if len(self.system.mass_points) <= target_count:
            print("Zielmasse erreicht.")
            # Auch wenn nicht löschen, für Plot rechnen
            u = self.solve_linear_system()
            self.current_displacements = u
            return

        # 1. FEM & Speichern
        u = self.solve_linear_system()
        self.current_displacements = u
        
        # 2. Wichtigkeit
        importance_map = self._calculate_point_importance(u)
        
        # 3. Löschen
        points_to_remove = self._identify_points_to_remove(importance_map)
        
        for pid in points_to_remove:
            self.system.remove_mass_point(pid)
            
        self.current_iteration += 1
        print(f"Iteration {self.current_iteration}: {len(points_to_remove)} Punkte entfernt.")

    def _calculate_point_importance(self, u: np.ndarray) -> dict[int, float]:
        """
        Berechnet Wichtigkeit mit 'Bridge Breaker' Logik.
        """
        raw_energies = {pid: 0.0 for pid in self.system.mass_points}
        for spring in self.system.springs:
            e = spring.calculate_strain_energy(u)
            if spring.point_a.id in raw_energies: raw_energies[spring.point_a.id] += 0.5 * e
            if spring.point_b.id in raw_energies: raw_energies[spring.point_b.id] += 0.5 * e

        filtered_energies = {}
        r_min = 3.5  
        
        active_points = list(self.system.mass_points.values())
        coords = {p.id: (p.x, p.z) for p in active_points}
        
        for p_i in active_points:
            weighted_sum = 0.0
            weight_total = 0.0
            for p_j in active_points:
                if abs(p_i.x - p_j.x) > r_min or abs(p_i.z - p_j.z) > r_min: continue
                dist = np.sqrt((p_i.x - p_j.x)**2 + (p_i.z - p_j.z)**2)
                if dist < r_min:
                    weight = (r_min - dist) ** 2
                    weighted_sum += weight * raw_energies[p_j.id]
                    weight_total += weight
            
            val = weighted_sum / weight_total if weight_total > 0 else raw_energies[p_i.id]
            filtered_energies[p_i.id] = val

        final_energies = {}
        check_radius = 1.5
        
        for p_i in active_points:
            neighbor_count = 0
            my_x, my_z = coords[p_i.id]
            
            for p_j in active_points:
                if p_i.id == p_j.id: continue
                if abs(my_x - p_j.x) > check_radius or abs(my_z - p_j.z) > check_radius: continue
                dist = np.sqrt((my_x - p_j.x)**2 + (my_z - p_j.z)**2)
                if dist < check_radius:
                    neighbor_count += 1
            
            energy = filtered_energies[p_i.id]
            
            if neighbor_count <= 3:
                energy *= 0.1 
            
            final_energies[p_i.id] = energy

        damped_energies = {}
        for pid, energy in final_energies.items():
            prev = self.previous_energies.get(pid, energy)
            damped_energies[pid] = 0.5 * energy + 0.5 * prev
        
        self.previous_energies = damped_energies
        return damped_energies

    def _identify_points_to_remove(self, importance_map: dict[int, float]) -> list[int]:
        critical_points = []
        for pid, p in self.system.mass_points.items():
            if p.is_fixed_x or p.is_fixed_z or pid in self.system.external_forces:
                critical_points.append(pid)

        candidates = sorted(importance_map.items(), key=lambda x: x[1])
        desired_removal = max(1, int(len(self.system.mass_points) * 0.01))
        
        points_to_remove = []
        active_ids = set(self.system.mass_points.keys())
        
        for pid, _ in candidates:
            if len(points_to_remove) >= desired_removal: break
            if pid in critical_points: continue
            if pid not in active_ids: continue

            active_ids.remove(pid)
            if self._is_structure_connected(active_ids, critical_points):
                points_to_remove.append(pid)
            else:
                active_ids.add(pid)
        return points_to_remove

    def _is_structure_connected(self, active_ids: set, critical_points: list[int]) -> bool:
        if not critical_points: return True
        adj = {pid: [] for pid in active_ids}
        for s in self.system.springs:
            if s.point_a.id in active_ids and s.point_b.id in active_ids:
                adj[s.point_a.id].append(s.point_b.id)
                adj[s.point_b.id].append(s.point_a.id)
        start = critical_points[0]
        if start not in adj: return False
        visited = {start}
        queue = [start]
        while queue:
            node = queue.pop(0)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return all(cp in visited for cp in critical_points)