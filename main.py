import sys
import numpy as np
import matplotlib

matplotlib.use('QtAgg')
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QFrame, QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QFont, QPainter, QPen, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- Quantum Gate Definitions ---
GATES = {
    'I': np.array([[1, 0], [0, 1]], dtype=complex),
    'X': np.array([[0, 1], [1, 0]], dtype=complex),
    'Y': np.array([[0, -1j], [1j, 0]], dtype=complex),
    'Z': np.array([[1, 0], [0, -1]], dtype=complex),
    'H': (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex),
    'S': np.array([[1, 0], [0, 1j]], dtype=complex),
    'T': np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
}

# Projectors for controlled operations
P0 = np.array([[1, 0], [0, 0]], dtype=complex)
P1 = np.array([[0, 0], [0, 1]], dtype=complex)

# --- UI Styling ---
DARK_THEME = """
    QMainWindow { background-color: #161616; color: #f4f4f4;}
    QLabel { color: #f4f4f4; }
    QFrame#Toolbox { background-color: #262626; border-right: 1px solid #393939; }
    QFrame#CircuitContainer { background-color: #161616; border: 1px solid #393939; border-radius: 4px; }
    QScrollArea { border: none; background-color: #161616; }

    QLabel.Gate { 
        background-color: #0f62fe; color: white; border-radius: 4px; font-weight: bold; font-size: 16px;
    }
    QLabel.Gate:hover { border: 1px solid white; }
    QLabel.Gate_Pauli { background-color: #007d79; }
    QLabel.Gate_Phase { background-color: #8a3ffc; }

    /* Solid White Circle Control Node (IBM Quantum Style) */
    QLabel.Gate_Control { 
        background-color: #ffffff; border: 2px solid #ffffff; border-radius: 8px; color: transparent;
    }
    QLabel.Gate_Control:hover { background-color: #e0e0e0; border-color: #e0e0e0; }

    /* Probability Box */
    QLabel.ProbabilityBox {
        background-color: #393939; color: #ffffff; border-radius: 2px; font-weight: bold; font-family: monospace; font-size: 14px;
    }

    QPushButton.ActionBtn { 
        background-color: #393939; color: white; border-radius: 4px; padding: 6px 14px; font-weight: bold; border: none;
    }
    QPushButton.ActionBtn:hover { background-color: #4c4c4c; }
    QPushButton.ActionBtn:pressed { background-color: #555555; }
"""


def build_multi_qubit_matrix(num_qubits, gate_dict):
    """Constructs an N-qubit operator via tensor products. Wire 0 is MSB."""
    mat = np.eye(1)
    for i in range(num_qubits):
        current_op = gate_dict.get(i, np.eye(2))
        mat = np.kron(mat, current_op)
    return mat


class GateWidget(QLabel):
    def __init__(self, gate_name, is_toolbox_item=True):
        super().__init__(gate_name if gate_name != 'CTRL' else '')
        self.gate_name = gate_name
        self.is_toolbox_item = is_toolbox_item

        # Dimensions
        if gate_name == 'CTRL':
            self.setFixedSize(16, 16)  # Clean small control dot size
        else:
            self.setFixedSize(40, 40)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.is_toolbox_item:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Click to remove")

        # Assign CSS Classes
        if gate_name == 'CTRL':
            self.setProperty('class', 'Gate_Control')
        elif gate_name in ['X', 'Y', 'Z']:
            self.setProperty('class', 'Gate Gate_Pauli')
        elif gate_name in ['S', 'T']:
            self.setProperty('class', 'Gate Gate_Phase')
        else:
            self.setProperty('class', 'Gate')

    def mousePressEvent(self, event):
        if self.is_toolbox_item:
            if event.button() == Qt.MouseButton.LeftButton:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.gate_name)
                drag.setMimeData(mime_data)

                # Setup visual drag representation
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.position().toPoint())
                drag.exec()
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
                parent = self.parentWidget()
                if hasattr(parent, 'remove_gate'):
                    parent.remove_gate(self)


class DropSlot(QFrame):
    def __init__(self, row, col, grid_manager):
        super().__init__()
        self.row = row
        self.col = col
        self.grid_manager = grid_manager
        self.setFixedSize(40, 40)
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gate_name = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        gate_name = event.mimeData().text()
        self.add_gate(gate_name)
        event.acceptProposedAction()

    def add_gate(self, gate_name):
        self.clear_slot()
        self.gate_name = gate_name
        gate_ui = GateWidget(gate_name, is_toolbox_item=False)
        self.layout.addWidget(gate_ui)
        self.grid_manager.main_window.update_simulation()

    def remove_gate(self, gate_widget):
        self.gate_name = None
        self.layout.removeWidget(gate_widget)
        gate_widget.deleteLater()
        self.grid_manager.main_window.update_simulation()

    def clear_slot(self):
        if self.layout.count() > 0:
            widget = self.layout.itemAt(0).widget()
            if widget:
                widget.deleteLater()
        self.gate_name = None


class ProbabilityBox(QLabel):
    """Displays the marginal probability of measuring |1>"""

    def __init__(self):
        super().__init__("0%")
        self.setFixedSize(50, 40)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setProperty('class', 'ProbabilityBox')

    def update_probability(self, prob_1):
        pct = int(round(prob_1 * 100))
        self.setText(f"{pct}%")

        # Visually indicate high probabilities
        if pct > 10:
            self.setStyleSheet(f"background-color: rgb(36, 161, 72); color: white; border-radius: 2px;")
        else:
            self.setStyleSheet("background-color: #393939; color: white; border-radius: 2px;")


class CircuitGrid(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("CircuitContainer")
        self.num_wires = 3
        self.num_cols = 12

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)

        self.state_labels = []
        self.slots = []
        self.prob_boxes = []

        self.build_grid()

    def build_grid(self):
        # Clear existing
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        self.state_labels.clear()
        self.slots.clear()
        self.prob_boxes.clear()

        for r in range(self.num_wires):
            row_slots = []

            # Initial state label
            lbl = QLabel(f"|0⟩")
            lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_layout.addWidget(lbl, r, 0)
            self.state_labels.append(lbl)

            # Gate slots
            for c in range(self.num_cols):
                slot = DropSlot(r, c, self)
                self.grid_layout.addWidget(slot, r, c + 1)
                row_slots.append(slot)
            self.slots.append(row_slots)

            # Probability Box
            prob_box = ProbabilityBox()
            # Push probability box further right to allow stretching
            self.grid_layout.addWidget(prob_box, r, self.num_cols + 2)
            self.prob_boxes.append(prob_box)

        # Apply column stretch to the empty column BEFORE the probability boxes
        self.grid_layout.setColumnStretch(self.num_cols + 1, 1)

    def add_wire(self):
        if self.num_wires < 8:  # Limit to 8 qubits to avoid heavy matrix explosions
            self.num_wires += 1
            self.build_grid()
            self.main_window.update_simulation()

    def remove_wire(self):
        if self.num_wires > 1:
            self.num_wires -= 1
            self.build_grid()
            self.main_window.update_simulation()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw horizontal wires
        pen = QPen(QColor("#666666"), 2)
        painter.setPen(pen)
        for r in range(self.num_wires):
            if not self.slots[r]: continue
            y = self.slots[r][0].geometry().center().y()
            start_x = self.state_labels[r].geometry().right() + 10
            end_x = self.prob_boxes[r].geometry().left() - 10
            painter.drawLine(start_x, y, end_x, y)

        # 2. Draw vertical multi-qubit linking lines
        pen.setColor(QColor("#ffffff"))
        pen.setWidth(3)
        painter.setPen(pen)

        for c in range(self.num_cols):
            active_rows = []
            for r in range(self.num_wires):
                if self.slots[r][c].gate_name is not None:
                    active_rows.append(r)

            if len(active_rows) > 1:
                # Only draw line if there's at least one CTRL and a target
                has_control = any(self.slots[r][c].gate_name == 'CTRL' for r in active_rows)
                has_target = any(self.slots[r][c].gate_name != 'CTRL' for r in active_rows)

                if has_control and has_target:
                    min_r, max_r = min(active_rows), max(active_rows)
                    x = self.slots[min_r][c].geometry().center().x()
                    y1 = self.slots[min_r][c].geometry().center().y()
                    y2 = self.slots[max_r][c].geometry().center().y()
                    painter.drawLine(x, y1, x, y2)

    def clear_circuit(self):
        for r in range(self.num_wires):
            for c in range(self.num_cols):
                self.slots[r][c].clear_slot()
        self.main_window.update_simulation()


class QuantumVisualizer(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(10, 5), facecolor='#161616')
        super().__init__(self.fig)
        self.ax_bloch = self.fig.add_subplot(121, projection='3d')
        self.ax_prob = self.fig.add_subplot(122)

        # Color palette for qubits
        self.colors = ['#0f62fe', '#da1e28', '#24a148', '#8a3ffc', '#ff832b', '#002d9c', '#a56eff', '#007d79']
        self.draw_initial()

    def draw_initial(self):
        state = np.zeros(8, dtype=complex)
        state[0] = 1.0
        self.update_visuals(state, [[0, 0, 1], [0, 0, 1], [0, 0, 1]], 3)

    def update_visuals(self, state_vector, bloch_vectors, num_qubits):
        self.ax_bloch.clear()
        self.ax_prob.clear()

        # FIX: Re-apply dark theme background colors after clear()
        self.ax_bloch.set_facecolor('#161616')
        self.ax_prob.set_facecolor('#161616')

        # --- Draw Multi-Qubit Bloch Sphere ---
        u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi:10j]
        x = np.cos(u) * np.sin(v)
        y = np.sin(u) * np.sin(v)
        z = np.cos(v)
        self.ax_bloch.plot_wireframe(x, y, z, color='#393939', linewidth=0.5)
        self.ax_bloch.plot([0, 0], [0, 0], [-1, 1], color='#555', linestyle='dashed')
        self.ax_bloch.plot([0, 0], [-1, 1], [0, 0], color='#555', linestyle='dashed')
        self.ax_bloch.plot([-1, 1], [0, 0], [0, 0], color='#555', linestyle='dashed')

        # Plot individual Bloch vectors for each wire
        for i, vector in enumerate(bloch_vectors):
            self.ax_bloch.quiver(0, 0, 0, vector[0], vector[1], vector[2],
                                 color=self.colors[i % len(self.colors)], length=1.0, normalize=False,
                                 arrow_length_ratio=0.2, linewidth=3, label=f"Q{i}")

        self.ax_bloch.set_xlim([-1, 1])
        self.ax_bloch.set_ylim([-1, 1])
        self.ax_bloch.set_zlim([-1, 1])
        self.ax_bloch.set_axis_off()

        # Enlarge the Bloch Sphere
        if hasattr(self.ax_bloch, 'set_box_aspect'):
            try:
                self.ax_bloch.set_box_aspect((1, 1, 1), zoom=1.5)
            except TypeError:
                pass  # Safe fallback for older Matplotlib versions

        self.ax_bloch.set_title("Bloch Sphere (Marginal States)", color='white', pad=20)

        # Shift the legend to avoid overlapping the larger sphere
        self.ax_bloch.legend(loc='upper left', facecolor='#262626', edgecolor='#393939', labelcolor='white',
                             bbox_to_anchor=(1.0, 1.05))

        # --- Draw Global System Probabilities ---
        probs = np.abs(state_vector) ** 2

        # IBM Quantum Style: if 4 or fewer qubits, show all possible basis states.
        if num_qubits <= 4:
            indices = np.arange(2 ** num_qubits)
        else:
            # Show only significant states to avoid dense text clutter
            indices = np.where(probs > 0.001)[0]
            if len(indices) == 0:
                indices = np.arange(min(8, 2 ** num_qubits))

        labels = [f"|{i:0{num_qubits}b}⟩" for i in indices]
        sig_probs = probs[indices]

        bars = self.ax_prob.bar(labels, sig_probs, color='#0f62fe', edgecolor='#393939')
        self.ax_prob.set_ylim([0, 1.1])
        self.ax_prob.tick_params(colors='white', axis='x', rotation=45 if num_qubits > 2 else 0)
        self.ax_prob.tick_params(colors='white', axis='y')
        self.ax_prob.set_title("Computational Basis Probabilities", color='white', pad=20)
        self.ax_prob.grid(axis='y', color='#393939', linestyle=':', alpha=0.4)

        for bar in bars:
            height = bar.get_height()
            self.ax_prob.annotate(f'{height * 100:.1f}%',
                                  xy=(bar.get_x() + bar.get_width() / 2, height),
                                  xytext=(0, 3), textcoords="offset points",
                                  ha='center', va='bottom', color='white', fontsize=9)

        self.fig.tight_layout()
        self.draw()


class QuantumApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Lab")
        self.resize(1400, 850)
        self.setStyleSheet(DARK_THEME)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 1. Toolbox (Left side) ---
        toolbox = QFrame()
        toolbox.setObjectName("Toolbox")
        toolbox.setFixedWidth(100)
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Controls Section
        ctrl_lbl = QLabel("Links")
        ctrl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        toolbox_layout.addWidget(ctrl_lbl)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #393939;")
        toolbox_layout.addWidget(line1)

        toolbox_layout.addWidget(GateWidget('CTRL', is_toolbox_item=True), alignment=Qt.AlignmentFlag.AlignHCenter)

        toolbox_layout.addSpacing(20)

        # Gates Section
        gates_lbl = QLabel("Gates")
        gates_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gates_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        toolbox_layout.addWidget(gates_lbl)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #393939;")
        toolbox_layout.addWidget(line2)

        for gate in ['H', 'X', 'Y', 'Z', 'S', 'T']:
            toolbox_layout.addWidget(GateWidget(gate, is_toolbox_item=True), alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addWidget(toolbox)

        # --- 2. Main Area (Right side) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Header controls
        circuit_header = QHBoxLayout()
        title_lbl = QLabel("Quantum Circuit")
        title_lbl.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        circuit_header.addWidget(title_lbl)
        circuit_header.addStretch()

        add_wire_btn = QPushButton("+ Add Qubit")
        add_wire_btn.setProperty('class', 'ActionBtn')
        add_wire_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        rem_wire_btn = QPushButton("- Remove Qubit")
        rem_wire_btn.setProperty('class', 'ActionBtn')
        rem_wire_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        clear_btn = QPushButton("Clear Circuit")
        clear_btn.setProperty('class', 'ActionBtn')
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        circuit_header.addWidget(add_wire_btn)
        circuit_header.addWidget(rem_wire_btn)
        circuit_header.addWidget(clear_btn)

        right_layout.addLayout(circuit_header)

        # Scrollable Circuit Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.circuit_grid = CircuitGrid(self)
        scroll_area.setWidget(self.circuit_grid)
        right_layout.addWidget(scroll_area, stretch=1)

        # Connect buttons
        clear_btn.clicked.connect(self.circuit_grid.clear_circuit)
        add_wire_btn.clicked.connect(self.circuit_grid.add_wire)
        rem_wire_btn.clicked.connect(self.circuit_grid.remove_wire)

        # Visualizer
        self.visualizer = QuantumVisualizer()
        right_layout.addWidget(self.visualizer, stretch=1)
        main_layout.addWidget(right_panel)

        # Initial launch update sync
        self.update_simulation()

    def get_expectation_value(self, state, num_qubits, qubit_idx, gate_name):
        operator = build_multi_qubit_matrix(num_qubits, {qubit_idx: GATES[gate_name]})
        return np.real(np.dot(np.conj(state), np.dot(operator, state)))

    def update_simulation(self):
        num_qubits = self.circuit_grid.num_wires
        state = np.zeros(2 ** num_qubits, dtype=complex)
        state[0] = 1.0  # Initial state |0...0>

        # Evaluate column by column
        for c in range(self.circuit_grid.num_cols):
            controls = []
            targets = {}

            for r in range(num_qubits):
                gate = self.circuit_grid.slots[r][c].gate_name
                if gate == 'CTRL':
                    controls.append(r)
                elif gate is not None:
                    targets[r] = gate

            if not controls and not targets:
                continue

            if controls and targets:
                # Construct Controlled Gate Matrix dynamically
                proj1_dict = {ctrl: P1 for ctrl in controls}
                P1_all = build_multi_qubit_matrix(num_qubits, proj1_dict)
                mat_identity_part = np.eye(2 ** num_qubits) - P1_all

                target_ops = {t: GATES[g] for t, g in targets.items()}
                combined_ops = {**proj1_dict, **target_ops}
                mat_controlled = build_multi_qubit_matrix(num_qubits, combined_ops)

                gate_matrix = mat_identity_part + mat_controlled
            else:
                # Construct Single Qubit Gates
                gate_dict = {t: GATES[g] for t, g in targets.items()}
                gate_matrix = build_multi_qubit_matrix(num_qubits, gate_dict)

            state = np.dot(gate_matrix, state)

        # Update UI: Calculate Marginal Probabilities & Bloch Vectors
        bloch_vectors = []
        for r in range(num_qubits):
            # Calculate probability of this specific wire measuring |1>
            prob1 = 0
            for i in range(len(state)):
                # Check if the r-th bit (from MSB) is 1
                if (i >> (num_qubits - 1 - r)) & 1:
                    prob1 += np.abs(state[i]) ** 2

            self.circuit_grid.prob_boxes[r].update_probability(prob1)

            # Calculate Bloch Sphere coordinates
            bx = self.get_expectation_value(state, num_qubits, r, 'X')
            by = self.get_expectation_value(state, num_qubits, r, 'Y')
            bz = self.get_expectation_value(state, num_qubits, r, 'Z')
            bloch_vectors.append([bx, by, bz])

        self.visualizer.update_visuals(state, bloch_vectors, num_qubits)

        # FIX: Force canvas refresh to instantly paint multi-qubit link lines
        self.circuit_grid.update()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QuantumApp()
    window.show()
    sys.exit(app.exec())