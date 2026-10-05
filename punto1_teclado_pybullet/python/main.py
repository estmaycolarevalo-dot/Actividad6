import argparse
import math
import os
import time

import pybullet as p
import pybullet_data

from digitos import TRAZOS

DIR = os.path.dirname(os.path.abspath(__file__))
URDF = os.path.join(DIR, "brazo.urdf")

DIST_PLANO = 0.48
Z_JOINT2 = 0.50
CENTRO_Z = 0.15
ANCHO = 0.12
ALTO = 0.20
ALCANCE_BASE = 0.42
LEVANTE = 0.03
VELOCIDAD = 0.30
DT = 1.0 / 240.0

ARTICULACIONES = ["joint_1", "joint_2", "joint_gripper"]
LIMITES = {"joint_1": (-2.5, 2.5), "joint_2": (-2.0, 2.0), "joint_gripper": (0.0, 0.15)}


def punto_a_articulaciones(y, z, levantado=False):
    zr = z - Z_JOINT2
    r = math.sqrt(DIST_PLANO ** 2 + y ** 2 + zr ** 2)
    q1 = math.atan2(y, DIST_PLANO)
    q2 = math.atan2(math.hypot(DIST_PLANO, y), zr)
    ext = r - ALCANCE_BASE - (LEVANTE if levantado else 0.0)
    q = [q1, q2, ext]
    return [min(max(v, LIMITES[n][0]), LIMITES[n][1]) for v, n in zip(q, ARTICULACIONES)]


def densificar(puntos, paso=0.006):
    salida = [puntos[0]]
    for (ya, za), (yb, zb) in zip(puntos, puntos[1:]):
        n = max(1, int(math.hypot(yb - ya, zb - za) / paso))
        salida += [(ya + (yb - ya) * i / n, za + (zb - za) * i / n) for i in range(1, n + 1)]
    return salida


def plano_desde_digito(u, v):
    return -(u - 0.5) * ANCHO, Z_JOINT2 + CENTRO_Z + (v - 0.5) * ALTO


class Brazo:
    def __init__(self, gui=True):
        self.gui = gui
        p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        self.id = p.loadURDF(URDF, [0, 0, 0], useFixedBase=True)
        self.idx = {}
        for i in range(p.getNumJoints(self.id)):
            self.idx[p.getJointInfo(self.id, i)[1].decode()] = i
        self.lineas = []
        self.ultimo = None
        self._crear_lienzo()
        if gui:
            p.resetDebugVisualizerCamera(1.4, 55, -15, [0.25, 0, 0.5])

    def _crear_lienzo(self):
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.002, 0.11, 0.14],
                                  rgbaColor=[1, 1, 1, 1])
        p.createMultiBody(0, -1, vis, [DIST_PLANO + 0.004, 0, Z_JOINT2 + CENTRO_Z])

    def punta(self):
        estado = p.getLinkState(self.id, self.idx["joint_gripper"], computeForwardKinematics=True)
        return p.multiplyTransforms(estado[4], estado[5], [0, 0, 0.12], [0, 0, 0, 1])[0]

    def ir_a(self, q, pasos, dibujar=False):
        pasos = max(1, int(pasos))
        inicio = [p.getJointState(self.id, self.idx[n])[0] for n in ARTICULACIONES]
        for k in range(1, pasos + 1):
            t = k / pasos
            for n, a, b in zip(ARTICULACIONES, inicio, q):
                p.setJointMotorControl2(self.id, self.idx[n], p.POSITION_CONTROL,
                                        targetPosition=a + (b - a) * t,
                                        force=500, positionGain=0.5, velocityGain=1.0)
            p.stepSimulation()
            if dibujar and k % 3 == 0:
                self._marcar()
            if self.gui:
                time.sleep(DT)

    def _marcar(self):
        punta = self.punta()
        if self.ultimo is not None:
            self.lineas.append(p.addUserDebugLine(self.ultimo, punta, [0.05, 0.05, 0.05], 4, 0))
        self.ultimo = punta

    def borrar(self):
        for i in self.lineas:
            p.removeUserDebugItem(i)
        self.lineas = []
        self.ultimo = None

    def dibujar_digito(self, digito):
        self.borrar()
        for trazo in TRAZOS[digito]:
            puntos = densificar([plano_desde_digito(u, v) for u, v in trazo])
            y0, z0 = puntos[0]
            self.ir_a(punto_a_articulaciones(y0, z0, True), 80)
            self.ir_a(punto_a_articulaciones(y0, z0, False), 25)
            self.ultimo = self.punta()
            for (ya, za), (yb, zb) in zip(puntos, puntos[1:]):
                pasos = math.hypot(yb - ya, zb - za) / (VELOCIDAD * DT)
                self.ir_a(punto_a_articulaciones(yb, zb, False), pasos, dibujar=True)
            self._marcar()
            self.ultimo = None
            yf, zf = puntos[-1]
            self.ir_a(punto_a_articulaciones(yf, zf, True), 25)
        self.ir_a([0.0, 0.0, 0.0], 100)


def conectar_serial(puerto, baud):
    import serial
    try:
        s = serial.Serial(puerto, baud, timeout=0.02)
        time.sleep(2)
        print(f"Conectado a la ESP32 en {puerto}")
        return s
    except Exception as e:
        print(f"No se pudo abrir {puerto}: {e}")
        return None


def simulador_activo():
    try:
        p.getNumBodies()
        return True
    except p.error:
        return False


def procesar(brazo, tecla, ser=None):
    if tecla == "#":
        brazo.borrar()
    elif tecla in TRAZOS:
        print(f"Tecla {tecla}: dibujando")
        if ser:
            ser.write(f"Dibujando: {tecla}\n".encode())
        brazo.dibujar_digito(tecla)
        if ser:
            ser.write(b"Listo\n")
            ser.reset_input_buffer()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM5")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--sin-serial", action="store_true")
    args = ap.parse_args()

    ser = None if args.sin_serial else conectar_serial(args.puerto, args.baud)
    if ser is None and not args.sin_serial:
        print("Continuando sin ESP32: escribe los dígitos por teclado.")
    brazo = Brazo(gui=True)

    try:
        while simulador_activo():
            if ser:
                linea = ser.readline().decode(errors="ignore").strip()
                if linea:
                    procesar(brazo, linea[0], ser)
            else:
                entrada = input("Tecla (0-9, # borra, q sale): ").strip()
                if entrada == "q":
                    break
                if entrada:
                    procesar(brazo, entrada[0])
    except (KeyboardInterrupt, p.error):
        pass
    if ser:
        ser.close()
    if simulador_activo():
        p.disconnect()


if __name__ == "__main__":
    main()
