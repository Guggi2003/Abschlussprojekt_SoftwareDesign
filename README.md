# Abschlussprojekt_SoftwareDesign
Abschlussprojekt für das Vorlesung Softwaredesing

Projektmitarbeiter:
  Kofler Michael
  Guggenberger Philipp

## Bericht

## 1. Einleitung
Dieses Projekt realisiert einen iterativen Algorithmus zur Topologieoptimierung. Die Umsetzung erfolgte in Python unter Verwendung von **NumPy** für die Matrixoperationen und **Streamlit** für die interaktive Visualisierung.

## 2. Theoretische Grundlagen
Die Implementierung orientiert sich an den Methoden der Strukturoptimierung.

### 2.1. Physikalisches Modell (Ground Structure)
Der Entwurfsraum wird als **Masse-Feder-System** diskretisiert.
* **Knoten:** Repräsentieren Massenpunkte mit zwei Freiheitsgraden ($u_x, u_z$).
* **Kanten:** Lineare Federelemente verbinden die Knoten orthogonal und diagonal. Diagonalstäbe werden hinsichtlich ihrer Steifigkeit korrigiert ($k_{diag} = k \cdot \frac{1}{\sqrt{2}}$), um die längere geometrische Ausdehnung zu kompensieren.

### 2.2. FEM-Löser
Das Systemgleichgewicht wird über die **Direkte Steifigkeitsmethode** bestimmt:
$$K \cdot u = F$$
Wobei $K$ die globale Steifigkeitsmatrix, $u$ der Verschiebungsvektor und $F$ der Kraftvektor ist. Die Randbedingungen werden durch Zeilen- und Spaltenmanipulation der Matrix $K$ realisiert ("Einbauen der Lager").

### 2.3. Optimierungskriterium
Ziel ist die Maximierung der Steifigkeit (bzw. Minimierung der Compliance $C$). Als Sensitivitätsmaß für die Materialentfernung dient die elementweise **Dehnungsenergie**:
$$E_{element} = \frac{1}{2} u_e^T K_e u_e$$
Elemente mit geringer Dehnungsenergie tragen kaum zur Lastabtragung bei und werden iterativ entfernt.

### 2.4. Regularisierung und Stabilität
Um bekannte numerische Probleme der Topologieoptimierung zu lösen, wurden folgende Erweiterungen implementiert:
* **Sensitivity Filter:** Ein Radius-basierter Filter glättet die Sensitivitäten (Energiedichte). Dies verhindert numerische Instabilitäten.
* **Konnektivitäts-Check:** Eine Graphen-Traversierung (Breitensuche / BFS) stellt sicher, dass Kraftpfade zwischen Last und Lager niemals unterbrochen werden, um singuläre Matrizen zu vermeiden.

## 3. Struktur des Codes
Das Projekt folgt dem MVC-Pattern (Model-View-Controller) zur Trennung von Physik und Logik:

* **`structural_components.py`**: Definition der finiten Elemente (`LinearSpring`, `MassPoint`). Implementierung der lokalen Elementsteifigkeitsmatrizen.
* **`mechanical_system.py`** *(Model)*: Verwaltung der Topologie, Assemblierung der globalen Steifigkeitsmatrix $K$ und Verwaltung der Randbedingungen.
* **`topology_optimizer.py`** *(Controller)*: Implementierung des Optimierungsalgorithmus, des linearen Gleichungslösers (inkl. Behandlung von Singularitäten) und der Filtertechniken.
* **`main.py`** *(View)*: Benutzeroberfläche zur Definition von Randbedingungen (Lager, Lasten) und Visualisierung der Ergebnisse.

## 4. Installation und Ausführung

### Voraussetzungen
* Python 3.9+
* Bibliotheken: `numpy`, `streamlit`, `matplotlib`

### Installation
```bash
pip install -r requirements.txt
