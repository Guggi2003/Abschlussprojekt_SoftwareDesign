# Abschlussprojekt_SoftwareDesign  
Abschlussprojekt für die Vorlesung Softwaredesign  

Projektmitarbeiter:   
Guggenberger Philipp
Kofler Michael 

---

# Bericht

## 1. Einleitung

Dieses Projekt realisiert einen iterativen Algorithmus zur Topologieoptimierung.  
Die Umsetzung erfolgte in Python unter Verwendung von NumPy für die Matrixoperationen und Streamlit für die interaktive Visualisierung.

Ziel ist die Entwicklung eines strukturierten, modular aufgebauten Systems zur Simulation und Optimierung eines diskretisierten Tragwerksmodells mit integrierter grafischer Benutzeroberfläche.

---

## 2. Theoretische Grundlagen

Die Implementierung orientiert sich an klassischen Methoden der Strukturoptimierung.

---

### 2.1 Physikalisches Modell

Der Entwurfsraum wird als diskretisiertes Masse-Feder-System modelliert.

**Knoten (MassPoints)**  
Repräsentieren Massenpunkte mit zwei Freiheitsgraden:

- \( u_x \)  
- \( u_z \)

**Kanten (LinearSpring)**  
Lineare Federelemente verbinden die Knoten:

- orthogonal (horizontal / vertikal)  
- diagonal  

Diagonalstäbe werden hinsichtlich ihrer Steifigkeit angepasst:

\[
k_{diag} = k \cdot \frac{1}{2}
\]

Diese Korrektur berücksichtigt die größere geometrische Länge der Diagonalelemente.

---

### 2.2 FEM-Löser

Das Systemgleichgewicht wird mittels der Direkten Steifigkeitsmethode bestimmt:

\[
K \cdot u = F
\]

Dabei ist:

- \( K \) – globale Steifigkeitsmatrix  
- \( u \) – Verschiebungsvektor  
- \( F \) – globaler Kraftvektor  

Die Randbedingungen (Festlager, Loslager) werden durch gezielte Manipulation von Zeilen und Spalten der Matrix \( K \) implementiert („Einbauen der Lager“).

---

### 2.3 Optimierungskriterium

Ziel ist die Maximierung der Steifigkeit bzw. Minimierung der Compliance \( C \).

Die Compliance wird berechnet als:

\[
C = \frac{1}{2} u^T F
\]

Als Sensitivitätsmaß dient die elementweise Dehnungsenergie:

\[
E_{Element} = \frac{1}{2} u_e^T K_e u_e
\]

Elemente mit geringer Dehnungsenergie tragen kaum zur Lastabtragung bei und werden iterativ entfernt.

---

### 2.4 Regularisierung und Stabilität

Zur Vermeidung numerischer Instabilitäten wurden folgende Erweiterungen implementiert:

**Sensitivity Filter**  
Ein radiusbasierter Filter glättet die Energiedichten benachbarter Elemente.  
Dies verhindert Schachbrettmuster und instabile Lokallösungen.

**Konnektivitäts-Check**  
Eine Graphen-Traversierung (Breitensuche / BFS) stellt sicher, dass Last- und Lagerknoten stets über einen zusammenhängenden Kraftpfad verbunden bleiben.  
Dadurch werden singuläre Steifigkeitsmatrizen vermieden.

---

## 3. Struktur des Codes

Das Projekt folgt dem MVC-Pattern (Model–View–Controller), um Physik, Optimierungslogik und Benutzeroberfläche klar zu trennen.

### structural_components.py
Definition der finiten Elemente:

- `MassPoint`
- `LinearSpring`

Implementierung der lokalen Elementsteifigkeitsmatrizen.

---

### mechanical_system.py (Model)

- Verwaltung der Topologie  
- Assemblierung der globalen Steifigkeitsmatrix \( K \)  
- Verwaltung von Randbedingungen und Lasten  

---

### topology_optimizer.py (Controller)

- Implementierung des iterativen Optimierungsalgorithmus  
- Lösung des linearen Gleichungssystems  
- Behandlung numerischer Singularitäten  
- Sensitivity-Filter  
- Konnektivitätsprüfung  

---

### main.py (View)

Interaktive Benutzeroberfläche mit Streamlit:

- Definition von Randbedingungen (Festlager, Loslager)
- Definition von Lasten
- Iterative Optimierung
- Visualisierung der Struktur
- Darstellung von:
  - Masseverlauf
  - Nachgiebigkeitsverlauf
  - Relativer Verformungs-Heatmap
  - Fortschrittsanzeige
  - Finalem Optimierungsreport

Zusätzlich implementiert:

- Projekt-Speichern und -Laden (Pickle)
- PNG-Export der Struktur (Plotly + Kaleido)
- Validierung: Genau ein Festlager und ein Loslager erforderlich

---

## 4. Erweiterungen im aktuellen Stand

Im Vergleich zur Basisversion wurden folgende Funktionen ergänzt:

- Speicherung und Verlauf der Nachgiebigkeit
- Relativer Steifigkeitsvergleich zur Startstruktur
- Fortschrittsanzeige in Prozent
- Finaler Report mit:
  - Materialeinsparung
  - Nachgiebigkeitsfaktor
  - Verbleibender Steifigkeit
- Relative Verformungs-Heatmap basierend auf initialem Maximalwert
- Konsistente Zurücksetzung der Historien bei Setup-Änderungen

---

## 5. Installation und Ausführung

### Voraussetzungen

- Python 3.9+
- Bibliotheken:
  - numpy
  - streamlit
  - pandas
  - plotly
  - kaleido (optional für PNG-Export)

---

## 6. Erweiterbarkeit auf 3D

Eine Erweiterung des Modells auf drei Dimensionen ist aus mathematischer Sicht grundsätzlich möglich.  
Die Formulierung der Steifigkeitsmatrix, der Freiheitsgrade sowie der Optimierungskriterien lässt sich direkt auf 3D übertragen.

Allerdings entsteht dabei ein massives Skalierungsproblem:

Beispielhafte Diskretisierung:

\[
60 \times 20 \times 20 = 24\,000 \text{ Knoten}
\]

In 3D besitzt jeder Knoten drei Freiheitsgrade:

- \( u_x \)
- \( u_y \)
- \( u_z \)

Damit ergibt sich:

\[
24\,000 \times 3 = 72\,000 \text{ Freiheitsgrade}
\]

Die globale Steifigkeitsmatrix \( K \) hat somit die Dimension:

\[
72\,000 \times 72\,000
\]

Das entspricht:

\[
5{,}184{,}000{,}000 \approx 5{,}1 \text{ Milliarden Matrixeinträgen}
\]

Die Verarbeitung einer Matrix dieser Größe ist mit einer dichten Darstellung rechnerisch und speichertechnisch äußerst aufwendig.  
Die Berechnungszeit würde selbst bei moderner Hardware stark ansteigen.

Aus diesem Grund wurde im Rahmen dieses Projekts bewusst eine 2D-Implementierung gewählt.

### Installation

```bash
pip install -r requirements.txt
