import mido
from lib import mtof
from lib import consts

#Handles input from MIDI devices, translating MIDI info into note-on, note-off, frequency, and velocity values
class MIDI_device:
    def __init__(self, device_name = consts.DEVICE_NAME):
        self._device_name = device_name
        self._input = None
        self._device_is_connected = self.connectController()
        self._mtof = mtof.mtof()

    #Handle incoming messages using callback
    #For parent class, this function just prints the MIDI information.
    #See the Synth subclass implementation for actual usasge
    def handleMessage(self, message):
        print("Base Class MIDI Callback entered")
        if message == None:
            raise TypeError("processMIDI got None (expected mido.Message)")
        if message.type == 'note_on':
            print(f"Note ON: {message.note}, Velocity: {message.velocity}")
        elif message.type == 'note_off':
            print(f"Note OFF: {message.note}, Velocity: {message.velocity}")
        elif message.type == 'control_change':
            print(f"Control Change: {message.control}, Value: {message.value}")

    def close(self):
        if self._input:
            self._input.close()

    #Find the correct device if possible    
    def connectController(self) -> bool:
        matching_ports = [port for port in mido.get_input_names() if self._device_name in port]
        if matching_ports:
            self._input = mido.open_input(matching_ports[0], callback=self.handleMessage)
            return True
        else:
            return False

    def printAllMIDIDevices(self):
        for device in mido.get_input_names():
            print(device)