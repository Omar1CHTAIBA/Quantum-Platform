# Quantum Lab 

Quantum Lab is an interactive, graphical quantum circuit simulator built with Python, PyQt6, and Matplotlib. It provides a visual playground to construct quantum circuits via drag-and-drop mechanics, compute multi-qubit state evolution, and visualize quantum states in real-time through marginal probabilities and 3D Bloch sphere projections.


# Demontration

<img width="1398" height="879" alt="Image" src="https://github.com/user-attachments/assets/0fb7dea0-16c0-49a1-9cc7-1d97869da3fb" />
<img width="1403" height="879" alt="Image" src="https://github.com/user-attachments/assets/8935e4a5-28dd-47e3-8ee5-901528bae5ca" />
<img width="1398" height="879" alt="Image" src="https://github.com/user-attachments/assets/9367bfd4-f34d-4964-a494-74a3282fb2f9" />

# Mathematical Framework

The core engine of Quantum Lab is a state-vector simulator powered by linear algebra, directly implementing the fundamental postulates of quantum mechanics. Below is a breakdown of the application's features and the physics driving them.

### 1. The Circuit Canvas & Quantum State
**Feature:** A dynamic grid where you can add up to 8 qubits and initialize the quantum state.
**The Math:** Unlike classical bits, a quantum bit (qubit) exists as a linear combination of basis states. An $n$-qubit system is represented by a normalized complex column vector $|\psi\rangle$ in a Hilbert space $\mathcal{H} = (\mathbb{C}^2)^{\otimes n}$ of dimension $2^n$. 

The simulator initializes the grid in the absolute ground state:
$$|\psi_0\rangle = |0\rangle^{\otimes n} = |0\dots0\rangle$$
In code, an 8-qubit system dynamically generates a complex state vector of $2^8 = 256$ dimensions.

### 2. Drag-and-Drop Single Qubit Gates

**Features:** Drag Pauli, Hadamard, and Phase gates onto the circuit wires to manipulate individual qubits.

**Pauli Gates (Fundamental Rotations):**

$$
X =
\begin{pmatrix}
0 & 1 \\
1 & 0
\end{pmatrix},
\quad
Y =
\begin{pmatrix}
0 & -i \\
i & 0
\end{pmatrix},
\quad
Z =
\begin{pmatrix}
1 & 0 \\
0 & -1
\end{pmatrix}
$$

**Hadamard Gate (Superposition Generator):**

$$
H =
\frac{1}{\sqrt{2}}
\begin{pmatrix}
1 & 1 \\
1 & -1
\end{pmatrix}
$$

**Phase Gates (Z-axis Rotations):**

$$
S =
\begin{pmatrix}
1 & 0 \\
0 & i
\end{pmatrix},
\quad
T =
\begin{pmatrix}
1 & 0 \\
0 & e^{i\pi/4}
\end{pmatrix}
$$


### 3. Multi-Target Control Links (Entanglement)
**Feature:** Link multiple control nodes (`CTRL`) to target gates to create complex entangling operations (like CNOT or Toffoli).
**The Math:** To apply local gates across an $n$-qubit state, the simulator uses the Kronecker product ($\otimes$) to build $2^n \times 2^n$ global matrices. Entanglement is generated using controlled operations. 

Using the projection operators $P_0 = |0\rangle\langle0|$ and $P_1 = |1\rangle\langle1|$, Quantum Lab splits the global unitary into two disjoint subspaces: the "un-triggered" identity subspace and the "triggered" operation subspace:
$$CU = \left( I^{\otimes n} - P_1^{(controls)} \right) + \left( P_1^{(controls)} \otimes U^{(targets)} \right)$$

### 4. Probability Histograms

**Feature:** View the global computational basis probabilities in the bar chart, and the marginal probability of measuring $|1\rangle$ at the end of each specific wire.
**The Math:** According to the Born rule, the quantum state is a superposition of basis states $|x\rangle$ with complex amplitudes $\alpha_x$:
$$|\psi\rangle = \sum_{x \in \{0,1\}^n} \alpha_x |x\rangle$$
The global probability of measuring any specific multi-qubit state $|x\rangle$ is the absolute square of its amplitude: $P(x) = |\alpha_x|^2$.

To display the **marginal probability** on individual wire terminals, the engine "traces out" the other qubits by summing the probabilities of all global basis states where that specific qubit $r$ is $1$:
$$P(|1\rangle_r) = \sum_{x \in \{0,1\}^n \,|\, x_r = 1} |\langle x | \psi \rangle|^2$$

### 5. 3D Bloch Sphere Visualizer
**Feature:** A real-time 3D rendering of the local state of each qubit.
**The Math:** When qubits are entangled, their individual local states cannot be described by a simple vector; they exist as *mixed states* described by a reduced density matrix $\rho_r = \text{Tr}_{\neq r}(|\psi\rangle\langle\psi|)$.

To map this to the 3D Bloch sphere, Quantum Lab calculates the Bloch vector $\vec{b} = (b_x, b_y, b_z)$ using the **expectation values** of the Pauli observables over the global state:
$$b_k = \langle \psi | (I \otimes \dots \otimes \sigma_k \otimes \dots \otimes I) | \psi \rangle, \quad \text{for } k \in \{X, Y, Z\}$$
*Interpretation:* If a qubit is purely independent, the vector touches the surface ($|\vec{b}| = 1$). If the qubit becomes highly entangled with the system, local information is lost, the state becomes mixed, and the vector shrinks inside the sphere ($|\vec{b}| < 1$).


# Code Architecture

The application relies strictly on an object-oriented approach bridging PyQt6 UI components and NumPy simulation logic:

* **`GATES`:** Dictionary housing the core $2 \times 2$ unitary matrices.
* **`build_multi_qubit_matrix()`:** A recursive algorithmic utility utilizing `np.kron` to construct $2^n \times 2^n$ operators from local gates.
* **UI Components (`GateWidget`, `DropSlot`, `CircuitGrid`):** Handle stateful drag-and-drop logic, dynamic wire drawing, and logic-gate mapping.
* **Visualizer (`QuantumVisualizer`):** Embeds Matplotlib into the PyQt6 event loop, computing 3D projections for the Bloch sphere and auto-scaling probability histograms.
* **Core Engine (`update_simulation`):** Evaluates the circuit slice-by-slice (column-by-column). It constructs the global unitary matrices, executes the matrix-vector multiplication to evolve the state vector, derives local expectation values, and forces visual repaints.


# Installation & Usage

### Prerequisites
Ensure you have Python 3.8+ installed. Install the required dependencies using `pip`:
```bash
pip install PyQt6 numpy matplotlib
```





