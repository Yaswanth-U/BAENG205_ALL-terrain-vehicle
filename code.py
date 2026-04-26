#made to be run on ESP8266 in Micro python firmware
from machine import Pin, PWM
import time
import bluetooth
from micropython import const

# =========================
# MOTOR SETUP (same as before)
# =========================
IN1 = Pin(2, Pin.OUT)
IN2 = Pin(3, Pin.OUT)
ENA = PWM(Pin(4))
ENA.freq(1000)

IN3 = Pin(5, Pin.OUT)
IN4 = Pin(6, Pin.OUT)
ENB = PWM(Pin(7))
ENB.freq(1000)

# =========================
# RAMPING VARIABLES
# =========================
current_L = 0
current_R = 0

target_L = 0
target_R = 0

RAMP_STEP = 1500     # speed change per cycle
RAMP_DELAY = 0.02    # seconds

# =========================
# MOTOR CONTROL
# =========================
def apply_motor(left, right):
    # LEFT
    if left >= 0:
        IN1.high(); IN2.low()
    else:
        IN1.low(); IN2.high()
    ENA.duty_u16(min(abs(int(left)), 65535))

    # RIGHT
    if right >= 0:
        IN3.high(); IN4.low()
    else:
        IN3.low(); IN4.high()
    ENB.duty_u16(min(abs(int(right)), 65535))


def ramp_update():
    global current_L, current_R

    # LEFT ramp
    if current_L < target_L:
        current_L += RAMP_STEP
        if current_L > target_L:
            current_L = target_L
    elif current_L > target_L:
        current_L -= RAMP_STEP
        if current_L < target_L:
            current_L = target_L

    # RIGHT ramp
    if current_R < target_R:
        current_R += RAMP_STEP
        if current_R > target_R:
            current_R = target_R
    elif current_R > target_R:
        current_R -= RAMP_STEP
        if current_R < target_R:
            current_R = target_R

    apply_motor(current_L, current_R)

# =========================
# BLE UART SETUP
# =========================
UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
TX_UUID   = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
RX_UUID   = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

_UART_SERVICE = (
    UART_UUID,
    (
        (TX_UUID, bluetooth.FLAG_NOTIFY,),
        (RX_UUID, bluetooth.FLAG_WRITE,),
    ),
)

class BLEUART:
    def __init__(self, ble, name="RC_Tank"):
        self.ble = ble
        self.ble.active(True)
        self.ble.irq(self.irq)

        ((self.tx, self.rx),) = self.ble.gatts_register_services((_UART_SERVICE,))
        self.connections = set()

        self.payload = bluetooth.advertising_payload(name=name)
        self.ble.gap_advertise(100, self.payload)

    def irq(self, event, data):
        if event == 1:  # connect
            conn_handle, _, _ = data
            self.connections.add(conn_handle)

        elif event == 2:  # disconnect
            conn_handle, _, _ = data
            self.connections.remove(conn_handle)
            self.ble.gap_advertise(100, self.payload)

        elif event == 3:  # write
            buffer = self.ble.gatts_read(self.rx)
            handle_command(buffer.decode().strip())
# =========================
# COMMAND HANDLER
# =========================
def handle_command(cmd):
    global target_L, target_R

    print("CMD:", cmd)

    if cmd == "F":
        target_L = 40000
        target_R = 40000

    elif cmd == "B":
        target_L = -40000
        target_R = -40000

    elif cmd == "L":
        target_L = -30000
        target_R = 30000

    elif cmd == "R":
        target_L = 30000
        target_R = -30000

    elif cmd == "S":
        target_L = 0
        target_R = 0

    elif cmd.startswith("V"):
        try:
            vals = cmd[1:].split(",")
            target_L = int(vals[0])
            target_R = int(vals[1])
        except:
            print("Invalid V command")
# =========================
# MAIN LOOP
# =========================
ble = bluetooth.BLE()
uart = BLEUART(ble)
print("Bluetooth RC Ready")
while True:
    ramp_update()
    time.sleep(RAMP_DELAY)
