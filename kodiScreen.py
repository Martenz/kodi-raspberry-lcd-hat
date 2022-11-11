"""
Example to extract the frames and other parameters from an animated gif
and then run the animation on the display.
Usage:
python3 rgb_display_pillow_animated_gif.py
This example is for use on (Linux) computers that are using CPython with
Adafruit Blinka to support CircuitPython libraries. CircuitPython does
not support PIL/pillow (python imaging library)!
Author(s): Melissa LeBlanc-Williams for Adafruit Industries
"""
import os
import time
import digitalio
import board
from PIL import Image, ImageOps, ImageFont, ImageDraw
import numpy as np # pylint: disable=unused-import
import adafruit_rgb_display.ili9341 as ili9341
import adafruit_rgb_display.st7789 as st7789  # pylint: disable=unused-import
import adafruit_rgb_display.hx8357 as hx8357  # pylint: disable=unused-import
import adafruit_rgb_display.st7735 as st7735  # pylint: disable=unused-import
import adafruit_rgb_display.ssd1351 as ssd1351  # pylint: disable=unused-import
import adafruit_rgb_display.ssd1331 as ssd1331  # pylint: disable=unused-import

# Change to match your display
BUTTON_RIGHT = board.D26 #board.D21
BUTTON_LEFT = board.D5 #board.D20
BUTTON_UP = board.D6
BUTTON_DOWN = board.D19
BUTTON_PRESS = board.D13
BUTTON_KEY1 = board.D21
BUTTON_KEY2 = board.D20
BUTTON_KEY3 = board.D16

# Configuration for CS and DC pins (these are PiTFT defaults):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)

# Set this to None on the Mini PiTFT
reset_pin = digitalio.DigitalInOut(board.D27)

font = ImageFont.load_default()
BORDER = 2

def init_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.switch_to_input()
    button.pull = digitalio.Pull.UP
    return button

# pylint: disable=too-few-public-methods
class Frame:
    def __init__(self, duration=0):
        self.duration = duration
        self.image = None

# pylint: enable=too-few-public-methods

def scaleCropImage(image):

    image_ratio = image.width / image.height
    screen_ratio = disp_width / disp_height
    if screen_ratio < image_ratio:
        scaled_width = image.width * disp_height // image.height
        scaled_height = disp_height
    else:
        scaled_width = disp_width
        scaled_height = image.height * disp_width // image.width
    image = image.resize((scaled_width, scaled_height), Image.BICUBIC)

    # Crop and center the image
    x = scaled_width // 2 - disp_width // 2
    y = scaled_height // 2 - disp_height // 2
    image = image.crop((x, y, x + disp_width, y + disp_height))

    return image


class AnimatedGif:
    def __init__(self, display, width=None, height=None, folder=None):
        self._frame_count = 0
        self._loop = 0
        self._index = 0
        self._duration = 0
        self._gif_files = []
        self._frames = []
        self._index_menu = 0
        self._timer = 0

        if width is not None:
            self._width = width
        else:
            self._width = display.width
        if height is not None:
            self._height = height
        else:
            self._height = display.height
        self.display = display
        self.advance_button = init_button(BUTTON_RIGHT)
        self.back_button = init_button(BUTTON_LEFT)
        self.press_button = init_button(BUTTON_PRESS)
        self.up_button = init_button(BUTTON_UP)
        self.down_button = init_button(BUTTON_DOWN)
        if folder is not None:
            self.load_files(folder)
            self.run()

    def advance(self):
        self._index = (self._index + 1) % len(self._gif_files)

    def back(self):
        self._index = (self._index - 1 + len(self._gif_files)) % len(self._gif_files)

    def load_files(self, folder):
        print(os.listdir(folder))
        gif_files = [folder+'/'+f for f in os.listdir(folder) if f.endswith(".gif") and not f.startswith("._")]
        for gif_file in gif_files:
            image = Image.open(gif_file)
            # Only add animated Gifs
            if image.is_animated:
                self._gif_files.append(gif_file)

        print("Found", self._gif_files)
        if not self._gif_files:
            print("No Gif files found in current folder")
            exit()  # pylint: disable=consider-using-sys-exit

    def preload(self):
        image = Image.open(self._gif_files[self._index])

        print("Loading {}...".format(self._gif_files[self._index]))
        if "duration" in image.info:
            self._duration = image.info["duration"]
        else:
            self._duration = 0
        if "loop" in image.info:
            self._loop = image.info["loop"]
        else:
            self._loop = 1
        self._frame_count = image.n_frames
        self._frames.clear()
        for frame in range(self._frame_count):
            image.seek(frame)
            # Create blank image for drawing.
            # Make sure to create image with mode 'RGB' for full color.
            frame_object = Frame(duration=self._duration)
            if "duration" in image.info:
                frame_object.duration = image.info["duration"]
            frame_object.image = ImageOps.fit(  # pylint: disable=no-member
                image.convert("RGB"),
                (self._width, self._height),
                method=Image.ANTIALIAS,
                #color=(0, 0, 0),
                centering=(0.5, 0.5),
            )
            self._frames.append(frame_object)

    def play(self):
        self.preload()

        # Check if we have loaded any files first
        if not self._gif_files:
            print("There are no Gif Images loaded to Play")
            return ('None',False)
        while True:
            for frame_object in self._frames:
                start_time = time.monotonic()
                self.display.image(frame_object.image)
                if not self.advance_button.value:
                    self.advance()
                    return ('right',False)
                if not self.back_button.value:
                    self.back()
                    return ('left',False)
                if not self.press_button.value:
                    return ('press',False)
                while time.monotonic() < (start_time + frame_object.duration / 1000):
                    pass

            if self._loop == 1:
                return ('None',True)
            if self._loop > 0:
                self._loop -= 1

    def showMenu(self):

        image = Image.new('RGB', (disp_width,disp_height), 'greenyellow')
        draw = ImageDraw.Draw(image)
        texts = ["GIFs","COLORS","RESTART","CLOSE"]
        for ti in range(len(texts)):
            (font_width, font_height) = font.getsize(texts[ti])
            if (ti == self._index_menu):
                # draw.rounded_rectangle(
                #     (BORDER,
                #     (ti+1) * disp_height // (len(texts)+2) - font_height - BORDER,
                #     disp_width - BORDER - 1,
                #     (ti+1) * disp_height // (len(texts)+2) + font_height + BORDER),
                #     fill="black", outline="green",
                #     width=2, radius=5)
                draw.rectangle(
                    (BORDER,
                    (ti+1) * disp_height // (len(texts)+2) - font_height - BORDER,
                    disp_width - BORDER - 1,
                    (ti+1) * disp_height // (len(texts)+2) + font_height + BORDER),
                    outline='green',fill='black')
            draw.text(
                (disp_width // 2 - font_width // 2, (ti+1) * disp_height // (len(texts)+2) - font_height // 2),
                texts[ti],
                font=font,
                fill='white')

        disp.image(image)

        if not self.down_button.value:
            self._index_menu = self._index_menu + 1 if self._index_menu + 1 < len(texts) else 0
            return 'down'
        if not self.up_button.value:
            self._index_menu = self._index_menu - 1 if self._index_menu - 1 >= 0 else len(texts) - 1
            return 'up'
        if not self.press_button.value:
            return texts[self._index_menu].lower()

        if self._timer < 15:
            return 'wait'
        else:
            return 'close'  

    def randomColors(self):
        color = list(np.random.choice(range(256), size=3))
        image = Image.new('RGB', (disp_width,disp_height), (color[0],color[1],color[2]))
        disp.image(image)  
        starttime = time.time()
        wait_s = 10
        while time.time() - starttime < wait_s:                                  
            if not self.press_button.value:
                return 'press'
        return 'colors'


    def run(self):
        e = 'None'
        start_time = time.time()
        last_time = start_time
        while True:
            if (e in ['right','left','None','close','gifs']):
                e, auto_advance = self.play()
                if auto_advance:
                    self.advance()
                else:
                    print(e,auto_advance)
                last_time = time.time()
            elif (e in ['colors']):
                e = self.randomColors()
                last_time = time.time()
            elif (e in ['press','up','down','wait']):
                self._timer = round((time.time() - last_time), 2)
                e = self.showMenu()
                if (e in ['up','down','press']):
                    last_time = time.time()
                print(e,self._timer)
            elif (e in ['restart']):
                kodi_off = Image.open("images/kodi_off.jpg")
                image = ImageOps.fit(
                    kodi_off.convert("RGB"),
                    (disp_width, disp_height),
                    method=Image.ANTIALIAS,
                    #color=(0, 0, 0),
                    centering=(0.5, 0.5))

                disp.image(image)
                time.sleep(1)
                print("Restart Raspberry")
                os.system("sudo reboot now")
                break
            else:
                break


# Config for display baudrate (default max is 64mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# pylint: disable=line-too-long
# Create the display:
# disp = st7789.ST7789(spi, rotation=90,                            # 2.0" ST7789
# disp = st7789.ST7789(spi, height=240, y_offset=80, rotation=180,  # 1.3", 1.54" ST7789
# disp = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40, # 1.14" ST7789
# disp = hx8357.HX8357(spi, rotation=180,                           # 3.5" HX8357
# disp = st7735.ST7735R(spi, rotation=90,                           # 1.8" ST7735R
disp = st7735.ST7735R(spi, rotation=90, width=128, height=128, x_offset=2, y_offset=3,   # 1.44" ST7735R
# disp = st7735.ST7735R(spi, rotation=90, bgr=True,                 # 0.96" MiniTFT ST7735R
# disp = ssd1351.SSD1351(spi, rotation=180,                         # 1.5" SSD1351
# disp = ssd1351.SSD1351(spi, height=96, y_offset=32, rotation=180, # 1.27" SSD1351
# disp = ssd1331.SSD1331(spi, rotation=180,                         # 0.96" SSD1331
#disp = ili9341.ILI9341(
#    spi,
#    rotation=90,  # 2.2", 2.4", 2.8", 3.2" ILI9341
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)
# pylint: enable=line-too-long

if disp.rotation % 180 == 90:
    disp_height = disp.width  # we swap height/width to rotate it to landscape!
    disp_width = disp.height
else:
    disp_width = disp.width
    disp_height = disp.height

kodi_on = Image.open("images/kodi_on.jpg")

# Scale the image to the smaller screen dimension
#image = scaleCropImage(image)
image = ImageOps.fit(  # pylint: disable=no-member
                kodi_on.convert("RGB"),
                (disp_width, disp_height),
                method=Image.ANTIALIAS,
                #color=(0, 0, 0),
                centering=(0.5, 0.5),
            )

# Display image.
disp.image(image)

time.sleep(5)

gif_player = AnimatedGif(disp, width=disp_width, height=disp_height, folder="images")

#image = Image.new('RGB', (disp_width,disp_height), 'white')
kodi_off = Image.open("images/kodi_off.jpg")
image = ImageOps.fit(  # pylint: disable=no-member
                kodi_off.convert("RGB"),
                (disp_width, disp_height),
                method=Image.ANTIALIAS,
                #color=(0, 0, 0),
                centering=(0.5, 0.5),
            )

disp.image(image)

