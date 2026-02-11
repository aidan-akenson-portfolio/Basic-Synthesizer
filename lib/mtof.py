from lib import consts

#Calculation function, can call when latency isn't first priority
def mtof_calc(MIDI: int = -1) -> float: #default to A0
    
    #Don't convert non-note MIDI information
    if MIDI < 21 or MIDI > 108:
        raise ValueError("Only MIDI values between 21 and 108 (inclusive) have a frequency representation")
    
    #Convert based on fixed point A4 = MIDI 69 = 440Hz
    return 440 * (2 ** ((MIDI - consts.A_440) / 12))

def mton_calc(MIDI: int = -1) -> str: #default to A0
    
    #Don't convert non-note MIDI information
    if MIDI < 21 or MIDI > 108:
        raise ValueError("Only MIDI values between 21 and 108 (inclusive) have a note representation")
    
    iton_map = {
        0: 'A',
        1: 'A# / Bb',
        2: 'B',
        3: 'C',
        4: 'C# / Db',
        5: 'D',
        6: 'D# / Eb',
        7: 'E',
        8: 'F',
        9: 'F# / Gb',
        10: 'G',
        11: 'G# / Ab'
    }
    
    #Convert based on fixed point A4 = MIDI 69 = 440Hz
    return iton_map[(MIDI - 21) % 12]

#Object containing MIDI to note mappings. Create before realtime use, then reference as needed
class mton():

    #Init by populating dictionary
    def __init__(self):
        self._dictionary = dict()
        for i in range(0, 21):
            self._dictionary[i] = False
        for i in range(21, 109):
            self._dictionary[i] = mton_calc(i)
        for i in range(109, 128):
            self._dictionary[i] = False
    
    #Subscript operator []
    def __getitem__(self, key):
        return self._dictionary[key]
    
    #Debug / Reference
    def printAllMTON(self):
        for i in range(21, 109):
            print("MIDI: ", i, ", note: ", f'{self._dictionary[i]:.5}', sep="")

#Object containing MIDI to frequency mappings. Create before realtime use, then reference as needed
class mtof():

    #Init by populating dictionary
    def __init__(self):
        self._dictionary = dict()
        for i in range(0, 21):
            self._dictionary[i] = False
        for i in range(21, 109):
            self._dictionary[i] = mtof_calc(i)
        for i in range(109, 128):
            self._dictionary[i] = False
    
    #Subscript operator []
    def __getitem__(self, key):
        return self._dictionary[key]
    
    #Debug / Reference
    def printAllMTOF(self):
        for i in range(21, 109):
            print("MIDI: ", i, ", frequency: ", f'{self._dictionary[i]:.5}', sep="")