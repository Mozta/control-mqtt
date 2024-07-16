import cv2
import mediapipe as mp
import paho.mqtt.client as mqtt
import time

# Crear instancia del cliente MQTT
mqttc = mqtt.Client()

try:
    # Conectarse al broker
    mqttc.connect("mqtt.eclipseprojects.io", 1883, 60)
except Exception as e:
    print(f"Failed to connect to broker: {e}")
    exit(1)

# Método para publicar mensajes
def publish_message(client, topic, message):
    result = client.publish(topic, message)
    status = result[0]
    if status == 0:
        print(f"Message `{message}` sent to topic `{topic}`")
    else:
        print(f"Failed to send message to topic `{topic}`")


# Iniciar el loop en un hilo diferente
mqttc.loop_start()

# Inicializa MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.5,
                       max_num_hands=1)

# Configura los colores en BGR para OpenCV
red_color = (0, 0, 255)
green_color = (0, 255, 0)
white_color = (255, 255, 255)

# Inicializa la cámara
cap = cv2.VideoCapture(0)

# Muestra un mensaje de error si la cámara no se pudo abrir
if not cap.isOpened():
    print("Error: No se puede abrir la cámara")
    exit()

# Calcula el 40% del ancho y alto de la ventana una vez
success, image = cap.read()
height, width = image.shape[:2]
rect_width = int(width * 0.4)
rect_height = int(height * 0.4)
rect_start = (width // 2 - rect_width // 2, height // 2 - rect_height // 2)
rect_end = (width // 2 + rect_width // 2, height // 2 + rect_height // 2)
rect_center = (width // 2, height // 2)  # Centro del rectángulo
dist_x = rect_end[0] - rect_start[0]
dist_y = rect_end[1] - rect_start[1]

# Función para obtener la posición del mouse
def pos_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:
        print(f"x: {x}, y: {y}")


# Variables para controlar la frecuencia de publicación
last_publish_time = 0
publish_interval = 0.5  # segundos

while True:
    success, image = cap.read()
    if not success:
        continue

    # Invierte la imagen horizontalmente para corregir el efecto espejo
    image = cv2.flip(image, 1)

    # Convierte la imagen de BGR a RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Procesa la imagen y extrae la información de las manos
    results = hands.process(image_rgb)

    # Dibuja el rectángulo en la imagen
    cv2.rectangle(image, rect_start, rect_end, green_color, 2)

    # Dibuja el punto central en el color predeterminado (rojo)
    joystick_color = red_color  # Color predeterminado del 'joystick'
    joystick_position = rect_center  # Posición predeterminada del 'joystick'

    # Verifica si se detectaron manos en la imagen y extrae la información de la primera mano
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        central_landmark = hand_landmarks.landmark[9] # Punto central de la mano
        x_hand = int(central_landmark.x * width)
        y_hand = int(central_landmark.y * height)

        # Transformar x en un valor entre 0 y 180
        x = int((x_hand - rect_start[0]) * 180 / dist_x)
        y = int((y_hand - rect_start[1]) * 180 / dist_y)

        # Verifica si el punto está dentro del rectángulo
        if rect_start[0] <= x_hand <= rect_end[0] and rect_start[1] <= y_hand <= rect_end[1]:
            # Cambia el color a verde si la mano está dentro del rectángulo
            joystick_color = green_color
            # Mueve la posición del joystick
            joystick_position = (x_hand, y_hand)

            cv2.putText(image, f"Original x: {x_hand}, y: {y_hand}", (
                rect_start[0], rect_end[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, white_color, 1)
            cv2.putText(image, f"Normalized x: {x}, y: {y}", (
                rect_start[0], rect_end[1] + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, white_color, 1)

            current_time = time.time()
            if current_time - last_publish_time > publish_interval:
                # Publicar el valor de x en el tópico "FAB24/test"
                data = f"{x},{y}"
                publish_message(mqttc, "FAB24/test", data)
                last_publish_time = current_time

            # Obtener x e y del evento del mouse
            cv2.setMouseCallback('MediaPipe Hands', pos_mouse)

    # Dibuja el 'joystick' en la imagen
    cv2.circle(image, joystick_position, 10, joystick_color, -1)

    # Muestra la imagen con OpenCV y espera a que se presione la tecla 'Esc' para salir
    cv2.imshow('MediaPipe Hands', image)
    if cv2.waitKey(5) & 0xFF == 27:
        break

# Libera la cámara y cierra todas las ventanas
cap.release()
cv2.destroyAllWindows()
# Detener el loop
mqttc.loop_stop()
