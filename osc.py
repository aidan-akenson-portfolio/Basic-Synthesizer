import math
from lib import consts
from lib import mtof
import numpy as np

class osc():
    def __init__(self, wave_type = "Sine"):

        #Constant parameters
        self._wave_type = wave_type
        self._mtof = mtof.mtof()

        #Dictionary to hold wave and phase data
        self._bank = dict()
        self._current_positions = dict()

        #Initialize wavedata
        for i in range(21, 109):
            frequency = self._mtof[i]
            samples_per_period = int(round(consts.BITRATE / frequency))

            #Generate 4 periods per note
            self._bank[i] = self.generateWavedata(samples_per_period, frequency, i)

            #Initialize each wave's position
            self._current_positions[i] = 0

    #Generate phase-continuous samples
    def generateWavedata(self, n_samples: int = consts.BUFFER_SIZE, frequency: float = 200.00, MIDI: int = 0) -> list:
        
        #Create enough samples to fill the requested buffer size
        samples = np.zeros(n_samples, dtype=np.float64)

        #NOT the position as used for audio output, this tracks generation progress
        generation_phase = 0.000
        
        #Generate correct sample for specified parameters
        for i in range(0, n_samples):

            match self._wave_type:
                case "Sine":
                    samples[i] = math.sin(generation_phase)

                case "Square":
                    if generation_phase < math.pi:
                        samples[i] = 1
                    else:
                        samples[i] = -1

                case "Saw":
                    samples[i] = -1 * (1 - (2 * (generation_phase / (2 * math.pi)) - 1.0))

                case _:
                    pass

            #Advance phase, keep within reasonable range 
            generation_phase += (2 * math.pi * frequency) / consts.BITRATE
            if generation_phase > 2 * math.pi:
                generation_phase -= 2 * math.pi

        return samples
    
    #Return enough samples to fill the buffer size
    def __getitem__(self, MIDI_value) -> list:

        #Fetch data and phase for the required note
        wave = self._bank[MIDI_value]
        period = len(wave)
        position = self._current_positions[MIDI_value]

        #Initialise output buffer
        output = np.zeros(consts.BUFFER_SIZE, np.float64)

        #Track position within output buffer and number of samples still to populate
        output_position = 0
        remaining = consts.BUFFER_SIZE

        #Populate output buffer while it isn't full
        while remaining > 0:
            #Number of samples that can be populated at once, rather than one at a time
            chunk_size = min(period - position, remaining)
            output[output_position : output_position + chunk_size] = wave[position : position + chunk_size]

            #Update all position trackers
            output_position += chunk_size
            position = (position + chunk_size) % period
            remaining -= chunk_size

        #Remember current position!
        self._current_positions[MIDI_value] = position

        #Send buffer
        return output
    
    def drawWaveform(self, plot, pos: int = 0) -> None:
        plot.drawWaveform(self._bank[60], pos)

    def printWave(self) -> None:
        print_list = self.getWavedata(self._samples_per_period)
        for x in print_list:
            print(x, end=" ")
        print()