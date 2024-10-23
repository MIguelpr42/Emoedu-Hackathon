import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import cv2
import numpy as np
import base64
from fer import FER
import smtplib
from email.mime.text import MIMEText
import webbrowser
import threading

app = Flask(__name__)

# Configuramos la base de datos SQLite
def init_db():
    conn = sqlite3.connect('emoedu.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emociones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno TEXT,
            emocion TEXT,
            fecha_hora TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Función para registrar una emoción negativa en la base de datos
def registrar_emocion(alumno, emocion):
    conn = sqlite3.connect('emoedu.db')
    cursor = conn.cursor()
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO emociones (alumno, emocion, fecha_hora)
        VALUES (?, ?, ?)
    ''', (alumno, emocion, fecha_hora))
    conn.commit()
    conn.close()

# Configuramos el detector de emociones
emotion_detector = FER(mtcnn=True)

# Ruta para servir la página HTML principal
@app.route('/')
def index():
    return render_template('main.html')

# Ruta para procesar la detección de emociones
@app.route('/Emoedu/detect', methods=['POST'])
def detect_emotion():
    try:
        # Obtenemos la imagen en formato base64 desde la solicitud
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        image_bytes = np.frombuffer(base64.b64decode(image_data), np.uint8)
        frame = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)

        # Invertimos horizontalmente la imagen para que coincida con el efecto espejo del video
        frame = cv2.flip(frame, 1)

        # Detectamos las emociones en el frame
        results = emotion_detector.detect_emotions(frame)
        faces = []

        for index, result in enumerate(results):
            (x, y, w, h) = result['box']
            emotion = max(result['emotions'], key=result['emotions'].get)
            faces.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'emotion': emotion
            })

            # Si la emoción es negativa, registramos en la base de datos
            if emotion in ['frustration', 'confused']:
                registrar_emocion(f"Alumno {index + 1}", emotion)

            # Si la emoción es "frustration" y la confianza es alta, enviamos una alerta
            if emotion == 'frustration' and result['emotions'][emotion] > 0.7:
                send_alert_email()

        return jsonify({'faces': faces})

    except Exception as e:
        print(f"Error al procesar la imagen: {e}")
        return jsonify({'error': str(e)}), 500

def open_browser():
    webbrowser.open_new('http://localhost:5000/')

if __name__ == '__main__':
    init_db()  # Inicializamos la base de datos
    threading.Timer(1, open_browser).start()  # Abre el navegador automáticamente
    app.run(host='0.0.0.0', port=5000, debug=True)