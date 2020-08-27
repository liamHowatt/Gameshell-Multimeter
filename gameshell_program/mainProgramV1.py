import sys
sys.stderr = open("/home/cpi/multimeter/mainProgramV1.py.err", "w")

import gpio
import time
import math
import pygame
from statistics import mode, StatisticsError
import subprocess

#2 - 32
#4 - 229
#5 - 228
#3 - 33

CPI = 32
ARD = 229
DAT_IN = 228
DAT_OUT = 33
TIMEOUT = 0.01
BITS = 12
AVG_BUFFER = 10
GRAPH_DEFAULT_SPACING = 3

def exchange(dOut):
    # Trade 1 byte between CPI and Arduino.

    global cpiState, ardState

    ardState = gpio.read(ARD)

    dIn = 0
    for i in range(BITS):

        gpio.write(DAT_OUT, (dOut >> i) % 2)

        gpio.write(CPI, cpiState)
        cpiState = not cpiState

        starTime = time.time()
        while(gpio.read(ARD) == ardState):
            time.sleep(0.0001)
            if starTime + TIMEOUT < time.time():
                return -1
        ardState = not ardState

        dIn += gpio.read(DAT_IN) << i

    gpio.write(CPI, cpiState)
    cpiState = not cpiState

    return dIn

degtan = lambda x: math.tan(math.radians(x))
def prog_square_pts(width, progress, _max, pos):

    progress = min(360, max(0, progress * 360 / _max))

    half_width = width // 2

    pts = [(half_width, half_width), (half_width, 0)]
    
    if progress > 45:
        pts.append((width, 0))
    if progress > 135:
        pts.append((width, width))
    if progress > 225:
        pts.append((0, width))
    if progress > 315:
        pts.append((0, 0))

    if progress > 315:
        theta = -progress + 360
        pts.append(( half_width - degtan(theta)*half_width , 0))
    elif progress > 225:
        theta = -progress + 270
        pts.append((0, half_width + degtan(theta)*half_width))
    elif progress > 135:
        theta = -progress + 180
        pts.append((half_width + degtan(theta)*half_width, width))
    elif progress > 45:
        theta = -progress + 90
        pts.append((width, half_width - degtan(theta)*half_width))
    else:
        theta = progress
        pts.append((half_width + degtan(theta)*half_width , 0))
    
    pts = [(pt[0] + pos[0], pt[1] + pos[1]) for pt in pts]

    return pts

def debug(msg):
    background.blit(fontB.render(str(msg), True, (255, 255, 255)), (0, 0))

def prog_widget(pos, text, val, _max):
    SIZE = 44
    MARGIN = 8
    pygame.draw.rect(background, (74, 74, 74), (pos, (SIZE, SIZE)))
    pygame.draw.polygon(background, (0, 255, 255), prog_square_pts(SIZE, val, _max, pos))
    inn_sq_sz = SIZE - MARGIN * 2
    pygame.draw.rect(background, (0, 0, 0), ((pos[0] + MARGIN, pos[1] + MARGIN), (inn_sq_sz, inn_sq_sz)))
    txt = fontB.render(text, True, (255, 255, 255))
    txt_x = math.floor(SIZE / 2 - txt.get_width() / 2) + pos[0]
    background.blit(txt, (txt_x, pos[1] + MARGIN))
    txt = fontB.render(str(int(val)), True, (255, 255, 255))
    txt_x = math.floor(SIZE / 2 - txt.get_width() / 2) + pos[0]
    background.blit(txt, (txt_x, pos[1] + MARGIN + txt.get_height()))

def median(seq):
    seq.sort()
    return seq[len(seq) // 2]

    # l = len(seq)
    # l_2 = l // 2
    # if l % 2 == 1:
    #     return seq[l_2]
    # else:
    #     return (seq[l_2 - 1] + seq[l_2]) / 2

def _mode(seq):
    try:
        return mode(seq)
    except StatisticsError:
        return median(seq)

def approxVolts(adc_reading):
    # Functions produced with linear regression
    # from readings of an off-the-shelf multimeter.
    if adc_reading <= 10:
        return max(0.0, 0.0381734 * adc_reading - 0.0290498)
    else:
        return 0.0309252 * adc_reading + 0.129679

def approxCurrent(adc_reading):
    adc_volts = adc_reading * 5 / 1023
    current = adc_volts / 2.4
    return current

def approxOhms(adc_reading):
    # Functions produced with linear regression
    # from readings of an off-the-shelf multimeter.
    if adc_reading >= 1015:
        return math.inf
    else:
        return max(0.0, -1.9312e6 / (adc_reading - 1022.75) - 2151.174)

def mapFunc(x, in_min, in_max, out_min, out_max):
    if in_min == in_max:
        return (out_min + out_max) / 2
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

gpio.initialize(CPI, False)
gpio.initialize(ARD, True)
gpio.initialize(DAT_IN, True)
gpio.initialize(DAT_OUT, False)
ardState = gpio.read(ARD)
cpiState = True

new_reading = 0
readings = []
avg = 0
setting = 0
tol = 0

with open("/sys/devices/platform/backlight/backlight/backlight/brightness", "r") as f:
    bright = int(f.read())

vol_str = subprocess.run(
    "amixer get Master",
    shell=True,
    capture_output=True,
)
vol = int( vol_str.stdout.decode("UTF-8").split("%")[0].split("[")[1] )

buff = AVG_BUFFER

vPic = pygame.image.load("/home/cpi/multimeter/V.png")
iPic = pygame.image.load("/home/cpi/multimeter/I.png")
rPic = pygame.image.load("/home/cpi/multimeter/R.png")
setting_pics = [vPic, iPic, rPic]

graph = pygame.Surface((304, 47))
hist = []
oldSetting = 0
g_spacing = GRAPH_DEFAULT_SPACING

pygame.mixer.pre_init(44100, -16, 1, 32)
pygame.mixer.init()
pygame.init()

beep = pygame.mixer.Sound("/home/cpi/multimeter/2433.ogg")
beep.set_volume(0.0)
beep.play(-1)
is_beeping = False
do_beep = False

windowSize = (320, 240)
window = pygame.display.set_mode(windowSize, pygame.FULLSCREEN)
background = pygame.Surface(windowSize)

fontA = pygame.font.Font("/home/cpi/multimeter/Arial Narrow.ttf", 85)
fontB = pygame.font.Font("/home/cpi/multimeter/DejaVuSansMono.ttf", 10)
fontC = pygame.font.Font("/home/cpi/multimeter/DejaVuSansMono.ttf", 20)

clock = pygame.time.Clock()
while True:
    clock.tick(30)

    background.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                exit()
            elif event.key == pygame.K_KP_MINUS:
                if bright > 1:
                    bright -= 1
                    with open("/sys/devices/platform/backlight/backlight/backlight/brightness", "w") as f:
                        f.write(str(bright))
            elif event.key == pygame.K_KP_PLUS:
                if bright < 9:
                    bright += 1
                    with open("/sys/devices/platform/backlight/backlight/backlight/brightness", "w") as f:
                        f.write(str(bright))
            elif event.key == 32: # select key
                vol = max(0, vol - 10)
                subprocess.run("amixer set Master {}%".format(vol), shell=True)
            elif event.key == 13: # start key
                vol = min(100, vol + 10)
                subprocess.run("amixer set Master {}%".format(vol), shell=True)
            elif event.key == 274: # down key
                buff = max(1, buff - 1)
            elif event.key == 273: # up key
                buff = min(60, buff + 1)
            elif event.key == pygame.K_LEFT:
                g_spacing = max(1, g_spacing - 0.2)
            elif event.key == pygame.K_RIGHT:
                g_spacing = min(10, g_spacing + 0.2)
            #debug(event.key)
    
    do_beep = False

    dataIn = exchange(0)
    if dataIn != -1:
        new_reading, setting = divmod(dataIn, 0b100)
        readings.append(new_reading)
        if len(readings) >= buff:
            avg = median(readings)
            readings = []

        # setting: v, i, r
        if setting == 0:
            volts = approxVolts(avg)
            display = str(round(volts, 2))
            end = "V"
            plusOne = approxVolts(avg + 1)
            tol = (plusOne - volts) / 2
        elif setting == 1:
            current = approxCurrent(avg)
            display = str(round(current, 2))
            end = "A"
            plusOne = approxCurrent(avg + 1)
            tol = (plusOne - current) / 2
        else: #setting==2
            ohms = approxOhms(avg)
            if math.isinf(ohms):
                eng_ohms = ohms
                end = chr(937) #omega symbol
            elif ohms >= 1000000.0:
                eng_ohms = ohms / 1000000.0
                end = "M" + chr(937)
            elif ohms >= 1000.0:
                eng_ohms = ohms / 1000.0
                end = "k" + chr(937)
            else:
                eng_ohms = ohms
                end = chr(937)
            display = str(round(eng_ohms, 2))
            plusOne = approxOhms(avg + 1)
            minusOne = approxOhms(avg - 1)
            if math.isinf(plusOne):
                tol = (ohms - minusOne) / 2
            if minusOne == 0:
                tol = (plusOne - ohms) / 2
            else:
                tol = (plusOne - minusOne) / 4
            new_ohms = approxOhms(new_reading)
            if new_ohms <= 30:
                do_beep = True

    else:
        display = "meter off"
        end = ""

    display_surf = fontA.render(display, True, (255, 255, 255))
    background.blit(pygame.transform.scale(display_surf, (display_surf.get_width(), int(display_surf.get_height() * 1.5))), (8, 35))
    end_surf = fontA.render(end, True, (255, 255, 255))
    background.blit(pygame.transform.scale(end_surf, (end_surf.get_width(), int(end_surf.get_height() * 1.5))), (312 - end_surf.get_width(), 35))

    fps = clock.get_fps()
    prog_widget((8, 188), "FPS", fps, 30)
    with open("/sys/class/power_supply/axp20x-battery/capacity", "r") as f:
        bat = int(f.read())
    prog_widget((60, 188), "batt", bat, 100)
    prog_widget((112, 188), "ADC", new_reading, 1023)
    prog_widget((164, 188), "bri", bright, 9)
    prog_widget((216, 188), "vol", vol, 100)
    prog_widget((268, 188), "buff", buff, 60)

    background.blit(fontC.render(chr(177) + " ~" + str(round(tol, 3)) + ["V", "A", chr(937)][setting], True, (255, 255, 255)), (10, 161))

    background.blit(setting_pics[setting], (252, 161))

    graph.fill((0, 0, 0))
    if setting != oldSetting:
        oldSetting = setting
        hist = []
    hist.insert(0, new_reading)
    while len(hist) * g_spacing > 304:
        del hist[-1]
    hist_max = max(hist)
    hist_min = min(hist)
    pointset = []
    for i, val in enumerate(hist):
        pointset.append((
            i * g_spacing,
            mapFunc(val, hist_min, hist_max, 0, 46)
        ))
    if len(pointset) >= 2:
        pygame.draw.lines(graph, (255, 255, 255), False, pointset)
    background.blit(pygame.transform.flip(graph, True, True), (8, 8))

    if do_beep:
        if not is_beeping:
            beep.set_volume(1.0)
            is_beeping = True
    else:
        if is_beeping:
            beep.set_volume(0.0)
            is_beeping = False

    window.blit(background, (0, 0))
    pygame.display.flip()
