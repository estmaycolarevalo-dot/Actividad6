import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import time
import cv2
import numpy as np
import serial
import tensorflow as tf
PUERTO_SERIAL = 'COM5'
BAUD_RATE = 115200
FRAMES_ESTABLES = 4
FRAMES_SIN_DIGITO = 15

DIR = os.path.dirname(os.path.abspath(__file__))
try:
    esp_a = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Conectado a la ESP-A en {PUERTO_SERIAL}")
except Exception as e:
    print(f"No se pudo abrir {PUERTO_SERIAL}: {e}")
    esp_a = None
def enviar_digito(digito, confianza):
    print(f"Enviando a ESP-A: {digito} ({confianza}%)")
    if esp_a and esp_a.is_open:
        esp_a.write(f"{digito},{confianza}\n".encode())

def preprocesar_digito(roi):
    """
    Convierte un recorte BGR de la webcam en una imagen 28x28 tipo MNIST:
      - Fondo negro, dígito blanco
      - Centrado por centro de masa
      - Escalado a 20x20 con padding
    Devuelve (imagen_normalizada, caja) o (None, None) si no hay dígito.
    """
    if roi is None or roi.size == 0:
        return None, None
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gris, (5, 5), 0)
    umbral = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )
    contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None, None

    c = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None, None
    x, y, w, h = cv2.boundingRect(c)
    digito = umbral[y:y+h, x:x+w]
    if w > h:
        nuevo_w = 20
        nuevo_h = max(1, int(round(20 * h / w)))
    else:
        nuevo_h = 20
        nuevo_w = max(1, int(round(20 * w / h)))

    digito = cv2.resize(digito, (nuevo_w, nuevo_h),
                        interpolation=cv2.INTER_AREA)
    lienzo = np.zeros((28, 28), dtype=np.uint8)
    M = cv2.moments(digito)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        cx, cy = nuevo_w // 2, nuevo_h // 2

    desplaz_x = 14 - cx
    desplaz_y = 14 - cy

    for i in range(nuevo_h):
        for j in range(nuevo_w):
            yi = i + desplaz_y
            xj = j + desplaz_x
            if 0 <= yi < 28 and 0 <= xj < 28:
                lienzo[yi, xj] = digito[i, j]
    lienzo = lienzo / 255.0

    return lienzo, (x, y, w, h)
modelo = tf.keras.models.load_model(os.path.join(DIR, 'modelo_mnist_cnn.h5'))
print("Modelo cargado. Presiona 'q' para salir.")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("No se pudo abrir la cámara.")
    exit()
x1, y1, x2, y2 = 300, 100, 600, 400
historial = []
VENTANA = 5
ultimo_enviado = None
sin_digito = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    roi = frame[y1:y2, x1:x2].copy()
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    digito_procesado, bbox = preprocesar_digito(roi)
    if digito_procesado is None:
        sin_digito += 1
        if sin_digito > FRAMES_SIN_DIGITO:
            ultimo_enviado = None
            historial.clear()
    else:
        sin_digito = 0
        entrada = digito_procesado.reshape(1, 28, 28, 1)
        prediccion = modelo.predict(entrada, verbose=0)
        clase = int(np.argmax(prediccion))
        confianza = float(np.max(prediccion)) * 100
        historial.append(clase)
        if len(historial) > VENTANA:
            historial.pop(0)
        if confianza > 60:
            clase_estable = max(set(historial), key=historial.count)
            texto = f"Numero: {clase_estable} ({confianza:.1f}%)"
            if (historial.count(clase_estable) >= FRAMES_ESTABLES
                    and clase_estable != ultimo_enviado):
                enviar_digito(clase_estable, int(confianza))
                ultimo_enviado = clase_estable
            cv2.putText(frame, texto, (x1, y1 - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 255, 0), 2)
        vista = (digito_procesado * 255).astype(np.uint8)
        vista = cv2.resize(vista, (200, 200),
                           interpolation=cv2.INTER_NEAREST)
        cv2.imshow('Digito procesado (28x28 ampliado)', vista)
    cv2.imshow('Reconocimiento de digitos', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
if esp_a:
    esp_a.close()
