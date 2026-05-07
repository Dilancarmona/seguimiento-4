
from machine import Pin, I2C, ADC, PWM
import random
import ssd1306
import time

# ------------------ OLED ------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ------------------ BOTONES ------------------
btn_pausa = Pin(14, Pin.IN, Pin.PULL_UP)
btn_start = Pin(25, Pin.IN, Pin.PULL_UP)
btn_up = Pin(26, Pin.IN, Pin.PULL_UP)
btn_down = Pin(27, Pin.IN, Pin.PULL_UP)

# ------------------ JOYSTICK ------------------
joy_vert = ADC(Pin(35))
joy_horiz = ADC(Pin(32))
joy_vert.atten(ADC.ATTN_11DB)
joy_horiz.atten(ADC.ATTN_11DB)

centro_v = 2300
centro_h = 2300
deadzone = 1000

# ------------------ BUZZER ------------------
buzzer = PWM(Pin(15))
buzzer.duty(0)

def beep(freq, dur):
    buzzer.freq(freq)
    buzzer.duty(300)
    tiempo_sonido["fin"] = time.ticks_ms() + dur

tiempo_sonido = {"fin": 0}

def actualizar_sonido():
    if time.ticks_ms() > tiempo_sonido["fin"]:
        buzzer.duty(0)

# ------------------ SPRITES ------------------
sprite = [
"000000000000000000000000",
"000000000001010000000000",
"000000000011111000000000",
"000000000001110000000000",
"000000000000100000000000",
"000000000000000000000000",
]

hueso = [
"000000000000000000000000",
"000000000001010000000000",
"000000000001110000000000",
"000000000000100000000000",
"000000000000100000000000",
"000000000000100000000000",
"000000000000100000000000",
"000000000001110000000000",
"000000000001010000000000",
]

# ------------------ DIMENSIONES ------------------
ancho_player = len(sprite[0])
alto_player = len(sprite)

ancho_hueso = len(hueso[0])
alto_hueso = len(hueso)

# ------------------ FUNCIONES ------------------

def crear_obstaculo():
    return {
        "x": random.randint(0, 128),
        "y": random.randint(0, 64),
        "v": random.randint(3, 10),
        "h": random.randint(3, 10),
        "vx": random.choice([-1, 1]) * random.uniform(0.5, 2),
        "vy": random.choice([-1, 1]) * random.uniform(0.5, 2)
    }

def crear_hueso():
    return {
        "x": random.randint(0, 128 - ancho_hueso),
        "y": random.randint(0, 64 - alto_hueso)
    }

def dibujar_sprite(x, y, sprite):
    for i in range(len(sprite)):
        for j in range(len(sprite[0])):
            if sprite[i][j] == "1":
                oled.pixel(x + j, y + i, 1)

def leer_boton(boton):
    if not boton.value():
        time.sleep_ms(5)
        if not boton.value():
            while not boton.value():
                pass
            return True
    return False

# ------------------ MENU ------------------
def mostrar_menu():
    opcion = 0
    while True:
        oled.fill(0)
        oled.text("Selecciona modo", 0, 0)

        if leer_boton(btn_up):
            opcion -= 1
            beep(800,100)

        if leer_boton(btn_down):
            opcion += 1
            beep(800,100)

        opcion = max(0, min(2, opcion))

        modos = ["Clasico","ContraTiempo","Hardcore"]
        for i,m in enumerate(modos):
            pref = ">" if i==opcion else " "
            oled.text(pref+" "+m,0,15+i*15)

        if leer_boton(btn_start):
            beep(1200,200)
            return opcion

        actualizar_sonido()
        oled.show()

# ------------------ VARIABLES ------------------
estado = "MENU"
modo = 0

# ------------------ LOOP ------------------
while True:

    if estado == "MENU":
        modo = mostrar_menu()

        y = 30
        x_player = 10
        obstaculos = [crear_obstaculo()]
        huesos = []
        huesos_recogidos = 0
        tiempo_inicio = time.ticks_ms()

        ultimo_spawn = 0

        objetivo_huesos = 5
        tiempo_limite = 25000

        estado = "JUEGO"

    elif estado == "JUEGO":

        if leer_boton(btn_pausa):
            estado = "PAUSA"
            continue

        oled.fill(0)

        # -------- MOVIMIENTO --------
        val_v = joy_vert.read()
        val_h = joy_horiz.read()

        vel_y = 0 if abs(val_v-centro_v)<deadzone else -(val_v-centro_v)/2048*5
        vel_x = 0 if abs(val_h-centro_h)<deadzone else (val_h-centro_h)/2048*5

        y += vel_y
        x_player += vel_x

        y = max(0, min(64-alto_player, int(y)))
        x_player = max(0, min(128-ancho_player, int(x_player)))

        # -------- TIEMPO --------
        tiempo_actual = time.ticks_diff(time.ticks_ms(), tiempo_inicio)

        # -------- MODOS --------
        if modo == 1:
            if tiempo_limite - tiempo_actual <= 0:
                estado = "GAME_OVER"

            if huesos_recogidos >= objetivo_huesos:
                estado = "WIN"

        if modo == 2:
            velocidad_extra = 2
        else:
            velocidad_extra = 1

        # -------- OBSTACULOS --------
        for obs in obstaculos:
            obs["x"] += obs["vx"] * velocidad_extra
            obs["y"] += obs["vy"] * velocidad_extra

            if obs["x"] <= 0 or obs["x"] >= 128:
                obs["vx"] *= -1
            if obs["y"] <= 0 or obs["y"] >= 64:
                obs["vy"] *= -1

        if random.randint(0,50) == 0:
            obstaculos.append(crear_obstaculo())

        # -------- COLISION (FIX IMPORTANTE) --------
        margen = 3   # 🔥 evita muertes falsas

        for obs in obstaculos:
            if (x_player + margen < obs["x"] + obs["v"] - margen and
                x_player + ancho_player - margen > obs["x"] + margen and
                y + margen < obs["y"] + obs["h"] - margen and
                y + alto_player - margen > obs["y"] + margen):

                beep(200,300)
                estado = "GAME_OVER"

        # -------- HUESOS --------
        if modo == 0:
            if tiempo_actual - ultimo_spawn > 20000:
                ultimo_spawn = tiempo_actual
                if len(huesos) < 3:
                    huesos.append(crear_hueso())

        elif modo == 1:
            if random.randint(0,30)==0 and len(huesos)<5:
                huesos.append(crear_hueso())

        else:
            if random.randint(0,100)==0 and len(huesos)<3:
                huesos.append(crear_hueso())

        for h in huesos[:]:
            if (x_player < h["x"]+ancho_hueso and
                x_player+ancho_player > h["x"] and
                y < h["y"]+alto_hueso and
                y+alto_player > h["y"]):

                huesos.remove(h)
                huesos_recogidos += 1
                beep(1500,100)

        # -------- WIN CLASICO --------
        if modo == 0 and huesos_recogidos >= 3:
            estado = "WIN"

        # -------- DIBUJO --------
        dibujar_sprite(x_player,y,sprite)

        for obs in obstaculos:
            for i in range(obs["h"]):
                for j in range(obs["v"]):
                    oled.pixel(int(obs["x"])+j,int(obs["y"])+i,1)

        for h in huesos:
            dibujar_sprite(int(h["x"]),int(h["y"]),hueso)

        # -------- HUD --------
        if modo == 1:
            restante = max(0,(tiempo_limite-tiempo_actual)//1000)
            oled.text("T:"+str(restante),80,0)
            oled.text("H:"+str(huesos_recogidos)+"/5",0,0)
        else:
            oled.text("T:"+str(tiempo_actual//1000),80,0)
            oled.text("H:"+str(huesos_recogidos),0,0)

        oled.show()
        actualizar_sonido()

    elif estado == "PAUSA":
        oled.fill(0)
        oled.text("PAUSA",40,20)
        oled.text("START continuar",0,40)
        oled.show()

        if leer_boton(btn_start):
            estado = "JUEGO"

    elif estado == "GAME_OVER":
        oled.fill(0)
        oled.text("GAME OVER",20,20)
        oled.text("START menu",0,40)
        oled.show()

        if leer_boton(btn_start):
            estado = "MENU"

    elif estado == "WIN":
        oled.fill(0)
        oled.text("GANASTE!",20,20)
        oled.text("START menu",0,40)
        oled.show()

        if leer_boton(btn_start):
            estado = "MENU"
