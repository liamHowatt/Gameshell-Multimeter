import os


def initialize(pin, isInput):

    exists = os.path.isdir(f"/sys/class/gpio/gpio{pin}")
    if not exists:
        with open("/sys/class/gpio/export", "w") as f:
            f.write(str(pin))

    with open(f"/sys/class/gpio/gpio{pin}/direction", "w") as f:
        f.write("in" if isInput else "low")


def write(pin, state):

    with open(f"/sys/class/gpio/gpio{pin}/value", "w") as f:
        f.write("1" if state else "0")


def read(pin):

    with open(f"/sys/class/gpio/gpio{pin}/value", "r") as f:
        state = f.read()

    if state == '0\n':
        return False
    if state == '1\n':
        return True

    raise Exception("unexpected pin value")
