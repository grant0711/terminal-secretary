import sounddevice as sd

def list_devices():
    print(sd.query_devices())

if __name__ == "__main__":
    list_devices()
