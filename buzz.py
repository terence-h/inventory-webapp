import RPi.GPIO as GPIO
import time

# Set up GPIO
BUZZER_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

def buzz(seconds: float = 0.2):
    try:
        GPIO.output(BUZZER_PIN, GPIO.HIGH)  # Turn on the buzzer
        time.sleep(seconds)
        GPIO.output(BUZZER_PIN, GPIO.LOW)  # Turn off the buzzer
    finally:
        GPIO.cleanup()  # Clean up GPIO