import numpy as np
import math

from lib import consts

# See https://www.desmos.com/calculator/nrn6oabn6h for preliminary math

# Envelope generator object
class ADSR():

    def __init__(self, debug_mode: int = consts.DEBUG_MODE):    # Attack, Decay, Release in s, Sustain 0.0 - 1.0

        # Parameter values table
        self._attack = np.zeros(consts.MAX_MIDI + 1, dtype=np.float32)
        self._decay = np.zeros(consts.MAX_MIDI + 1, dtype=np.float32)
        self._sustain = np.zeros(consts.MAX_MIDI + 1, dtype=np.float32)
        self._release = np.zeros(consts.MAX_MIDI + 1, dtype=np.float32)
        for i in range(consts.MAX_MIDI + 1):
            self._attack[i] = int((consts.MIN_ATTACK + (i / consts.MAX_MIDI) * (consts.MAX_ATTACK - consts.MIN_ATTACK)) * consts.BITRATE)
            self._decay[i] = int((consts.MIN_DECAY + (i / consts.MAX_MIDI) * (consts.MAX_DECAY - consts.MIN_DECAY)) * consts.BITRATE)
            self._sustain[i] = consts.MIN_SUSTAIN + (i / consts.MAX_MIDI) * (consts.MAX_SUSTAIN - consts.MIN_SUSTAIN)
            self._release[i] = int((consts.MIN_RELEASE + (i / consts.MAX_MIDI) * (consts.MAX_RELEASE - consts.MIN_RELEASE)) * consts.BITRATE)

        # Initial envelope values
        self._A_param = 0
        self._D_param = 32
        self._S_param = 0
        self._R_param = 32

        # Array initializations, ensure enough samples to prevent non-flat sustain and post-release buffers
        self._array_size = consts.BITRATE // 10             

        # Array populations
        self._A_values = np.zeros(self._array_size, dtype=np.float32)
        self._D_values = np.zeros(self._array_size, dtype=np.float32)
        self._R_values = np.zeros(self._array_size, dtype=np.float32)
        self.generateA()
        self.generateD()
        self.generateR()
        self._empty_buffer = np.zeros(consts.BUFFER_SIZE, dtype=np.float32)

        # State tracking
        self._state = consts.OFF
        self._position = 0.0
        self._positions = np.empty(consts.BUFFER_SIZE, dtype=np.float32)
        self._value = 0.0

        self._debug_mode = debug_mode

    # Populate Atack array
    def generateA(self):
        for i in range(self._array_size):
            progress = i / (self._array_size - 1)
            self._A_values[i] = progress ** 2      #Quadratic attack
    # Populate Decay array
    def generateD(self):
        for i in range(self._array_size):
            progress = i / (self._array_size - 1)
            # Linear value
            linear_value = 1.0  - progress
            # Apply exponential decay function based on coefficient
            self._D_values[i] = (linear_value * math.e ** (- consts.EXPONENTIAL_DECAY_COEFFICIENT * progress))
    # Populate Release array
    def generateR(self):
        for i in range(self._array_size):
            progress = i / (self._array_size - 1)
            # Linear value
            linear_value = 1 - progress
            # Apply exponential decay function based on coefficient
            self._R_values[i] = linear_value * math.e ** (- consts.EXPONENTIAL_DECAY_COEFFICIENT * progress)

    def updateParameters(self, attack=None, decay=None, sustain=None, release=None):
        if attack is not None:
            self._A_param = attack
            return
        if decay is not None:
            self._D_param = decay
            return
        if sustain is not None:
            self._S_param = sustain
            return
        if release is not None:
            self._R_param = release
            return
        return

    def interpolateInArray(self, array, pos, len):
        scaled_pos = pos * (self._array_size - 1) / len
        if scaled_pos <= 0:
            return array[0]
        if scaled_pos >= self._array_size - 1:
            return array[self._array_size - 1]
        
        index = int(scaled_pos)
        fraction = scaled_pos - index

        # Linear interpolation
        return (array[index] * (1.0 - fraction)) + (array[index + 1] * fraction)

    # Return envelope data, increment buffer chunk
    def applyEnvelope(self, pre_env_data):

        # Populate buffers
        return_data = self._empty_buffer
        self._positions = np.arange(self._position, self._position + consts.BUFFER_SIZE)

        # Find appropriate stage of envelope
        match self._state:
            case consts.A:

                attack_samples = self._attack[self._A_param]

                mask = self._positions < attack_samples
                scaled_pos = self._positions * (self._array_size - 1) / attack_samples
                indices = np.clip(scaled_pos.astype(np.int32), 0, self._array_size - 2)
                fractions = scaled_pos - indices

                env_vals = np.where(mask, self._A_values[indices] * (1.0 - fractions) + self._A_values[indices + 1] * fractions, 1.0)   
                return_data = pre_env_data * env_vals
                
                self._value = env_vals[-1]
                self._position += consts.BUFFER_SIZE

                if self._position >= attack_samples:
                    self._state = consts.D
                    self._position = 0.0

                return return_data
            
            case consts.D:

                decay_samples = self._decay[self._D_param]

                mask = self._positions < decay_samples
                scaled_pos = self._positions * (self._array_size - 1) / decay_samples
                indices = np.clip(scaled_pos.astype(np.int32), 0, self._array_size - 2)
                fractions = scaled_pos - indices

                interpolated_vals = np.where(mask, self._D_values[indices] * (1.0 - fractions) + self._D_values[indices + 1] * fractions, 0.0) 
                env_vals = ((1 - self._sustain[self._S_param]) * interpolated_vals) + self._sustain[self._S_param]  
                return_data = pre_env_data * env_vals
                
                self._value = env_vals[-1]  
                self._position += consts.BUFFER_SIZE

                if self._position >= decay_samples:
                    self._state = consts.S
                    self._position = 0.0

                return return_data
            
            case consts.S:

                return_data = pre_env_data * self._sustain[self._S_param]

                self._value = self._sustain[self._S_param]
                self._position += consts.BUFFER_SIZE
                
                return return_data

            case consts.R:

                release_samples = self._release[self._R_param]
                
                scale_factor = max(self._sustain[self._S_param], self._value) * min(1, self._value / max(self._sustain[self._S_param], 0.00000000001))

                mask = self._positions < release_samples

                # Calculate for positions within release
                scaled_pos = np.clip(self._positions, 0, release_samples - 1) * (self._array_size - 1) / release_samples
                indices = np.clip(scaled_pos.astype(np.int32), 0, self._array_size - 2)
                fractions = scaled_pos - indices

                interpolated_vals = self._R_values[indices] * (1.0 - fractions) + self._R_values[indices + 1] * fractions 
                env_vals = np.where(mask, scale_factor * interpolated_vals, 0.0)

                return_data = pre_env_data * env_vals

                self._position += consts.BUFFER_SIZE

                # Turn off envelope if complete
                if self._position >= release_samples:
                    self.reset()
                    return np.zeros(consts.BUFFER_SIZE, float)
        
                return return_data

            case _:
                return return_data

    # Turn note on
    def start(self):
        self._state = consts.A
        self._position = 0.0
    # Change state from ADS to R, turn off if release is 0 immediately
    def release(self):
        if self._state > consts.OFF and self._state < consts.R:
            #Switch state, resetting position
            self._state = consts.R
            self._position = 0.0

    # Check state
    def isOn(self) -> bool:
        return self._state > consts.OFF and self._state <= consts.R
    def isOff(self) -> bool:
        return self._state == consts.OFF

    # Reset envelope to initial state (for after it has been "used up")
    def reset(self):
        self._state = consts.OFF
        self._position = 0.0
        self._value = 0.0

    # Visualize envelope
    def getEnvelopeData(self) -> np.array:

        attack_segment = self._A_values
        d_len = int(self._decay[self._D_param])
        decay_segment = np.zeros(d_len)
        for i in range(d_len):
            decay_segment[i] = ((1 - self._sustain[self._S_param]) * (self.interpolateInArray(self._D_values, i, d_len))) + self._sustain[self._S_param]
        s_len = int(self._array_size // 4)
        sustain_segment = np.full(s_len, fill_value=self._sustain[self._S_param])
        r_len = int(self._release[self._R_param])
        release_segment = np.zeros(r_len)
        scale_factor = self._sustain[self._S_param] * min(1, self._sustain[self._S_param] / max(self._sustain[self._S_param], 0.00000000001))
        for i in range(r_len):
            release_segment[i] = self.interpolateInArray(self._R_values, i, r_len) * scale_factor

        return np.concat((attack_segment, decay_segment, sustain_segment, release_segment))