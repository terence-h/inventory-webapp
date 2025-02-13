# from gpiozero import Buzzer
# from time import sleep

# bz = Buzzer(18)

# def buzz(seconds=0.2):
#     bz.on()
#     sleep(seconds)
#     bz.off()

from gpiozero import Buzzer

def create_buzzer():
    global bz
    try:
        bz = Buzzer(18, initial_value=False)
    except Exception as e:
        print(f"Buzzer init error: {e}")
        bz = None

def cleanup_gpio():
    if bz:
        bz.close()
    
def buzz():
    if bz:
        bz.beep(on_time=0.2, off_time=0.2, n=1)