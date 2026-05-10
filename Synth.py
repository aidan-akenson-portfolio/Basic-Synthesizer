import numpy as np
import time
import copy

import MIDI_input as MIDI
import Output_Stream
import osc
import ADSR
import Filter
import Parameter_Interface
import IR_Reverb

from lib import mtof
from lib import consts

UNUSED = -1


#"Hub" class, defines signal flow up until Output_Stream
#   -IS A MIDI_device object
#   -HAS A(N) oscillator (osc)
#   -         envelope (ADSR)     see https://www.desmos.com/calculator/nrn6oabn6h for math
#   -         Filter (Filter)
#
class Synth(MIDI.MIDI_device):
    def __init__(self, debug_mode: int = consts.DEBUG_MODE, amplitude: float = 1.0):
        
        start = time.perf_counter()

        super().__init__(consts.DEVICE_NAME)
        
        self._debug_mode = debug_mode #0 --- No debug outputs
                                      #1 --- Simple debug outputs
                                      #2 --- Verbose debug outputs
                                      #3 --- Efficiency debug outputs

        if self._debug_mode == 3:
            base_class_timer = time.perf_counter() - start

        #Signal generation components
        self._amplitude = amplitude
        self._wave_type = consts.WAVE_TYPE
        self._sin= osc.osc("Sine")
        self._saw = osc.osc("Saw")
        self._sqr = osc.osc("Square")
        match self._wave_type:
            case "Sine":
                self._osc = self._sin
            case "Saw":
                self._osc = self._saw
            case "Square":
                self._osc = self._sqr

        if self._debug_mode == 3:
            osc_gen_timer = time.perf_counter() - start
        
        #Voice handler
        self._voices = []
        for i in range(consts.MAX_VOICES):
            self._voices.append(UNUSED)
        
        #Filter, cascading two 2-pole filters
        self._filter1_left = Filter.Filter()
        self._filter1_right = Filter.Filter()
        self._filter2 = Filter.Filter()

        if self._debug_mode == 3:
            filter_timer = time.perf_counter() - start

        #Envelope generator
        self._envelopes = []
        envelope = ADSR.ADSR(self._debug_mode)
        for e in range(consts.MAX_VOICES):
            self._envelopes.append(copy.deepcopy(envelope))

        if self._debug_mode == 3:
            env_timer = time.perf_counter() - start

        #Reverb
        self._reverb = IR_Reverb.IR(ir=consts.IR)
        
        if self._debug_mode == 3:
            reverb_timer = time.perf_counter() - start

        #Mtof and Mton converters, just in case
        self._mtof = mtof.mtof()
        self._mton = mtof.mton()

        if self._debug_mode == 3:
            midi_conv_timer = time.perf_counter() - start
        
        #If parameters have updated, this lets the manager class know
        self._needs_redraw = True

        #Parameter controller
        self._Parameter_Interface = Parameter_Interface.Parameter_Interface()

        if self._debug_mode == 3:
            vis_timer = time.perf_counter() - start

        #Initialize output stream
        self._output = Output_Stream.output(self._debug_mode)
        #Only use debug buffer providers if debug enabled
        if self._debug_mode == 3:
            if consts.FILTER_ON == True:
                match consts.POLES:
                    case 2:
                        self._output.play(self.getDebug2PoleFilterAudioBuffer)
                    case 4:
                        self._output.play(self.getDebug4PoleFilterAudioBuffer)
            else:
                self._output.play(self.getDebugAudioBuffer)
        #Only use filter buffer providers as appropriate
        elif consts.FILTER_ON == True:
            match consts.POLES:
                case 2:
                    self._output.play(self.get2PoleFilterAudioBuffer)
                case 4:
                    self._output.play(self.get4PoleFilterAudioBuffer)
        #Default buffer provider
        else:
            self._output.play(self.getAudioBuffer)
        
        if self._debug_mode == 3:
            out_stream_timer = time.perf_counter() - start
            print()
            print(f"====================BOOTUP=INFO====================")
            print()
            print(f"\tBase Class initialized in: {(1000 * base_class_timer):.2f}ms")
            print(f"\tOscillator bank populated in: {(1000 * (osc_gen_timer - base_class_timer)):.2f}ms")
            print(f"\tFilter initialized in: {(1000 * (filter_timer - osc_gen_timer)):.2f}ms")
            print(f"\tEnvelopes initialized in: {(1000 * (env_timer - filter_timer)):.2f}ms")
            print(f"\tReverb initialized in: {(1000 * (reverb_timer - env_timer)):.2f}ms")
            print(f"\tMIDI converters initialized in: {(1000 * (midi_conv_timer - env_timer)):.2f}ms")
            print(f"\tVisualizer initialized in: {(1000 * (vis_timer - midi_conv_timer)):.2f}ms")
            print(f"\tOutput stream initialized in: {(1000 * (out_stream_timer - vis_timer)):.2f}ms")
            print()
            print(f"TOTAL INTERNAL BOOT TIME: {(1000 * out_stream_timer):.2f}ms ({(out_stream_timer):.2f}s)")
            print(f"===================================================")

        if self._debug_mode > 0 and self._debug_mode < 3:
            self.printAllMIDIDevices()
            print("Connected to MIDI input:", self._device_is_connected)

    #Overloaded MIDI handler method, updates oscillator frequency, starts and stops playback
    def handleMessage(self, message):

        #Comment out to improve performance
        #if self._debug_mode == 2:
        #    print("Synth MIDI Callback entered")

        #Update oscillator based on new frequency and trigger ADSR start
        if message.type == 'note_on' and self._mtof[message.note]:

            self.addVoice(message.note)

            if not self._output._isPlaying:
                self._output._isPlaying = True

        #Trigger ADSR release
        elif message.type == 'note_off':
            
            self.releaseVoice(message.note)

            #If no voices are active, stop playing
            active_voices = [v for v in self._voices if v != UNUSED]
            if not active_voices:
                self._output._isPlaying = False

        # Update any parameters mapped to CC
        elif message.type == 'control_change':

            if self._debug_mode == 2:
                print(f"Control Change: {message.control}, Value: {message.value}")

            # ADSR parameters handled using ADSR bank class
            match message.control:
                case consts.ATTACK_CC:
                    for e in self._envelopes:
                        e.updateParameters(attack=message.value)
                    self._needs_redraw = True
                    return
                case consts.DECAY_CC:
                    for e in self._envelopes:
                        e.updateParameters(decay=message.value)
                    self._needs_redraw = True
                    return
                case consts.SUSTAIN_CC:
                    for e in self._envelopes:
                        e.updateParameters(sustain=message.value)
                    self._needs_redraw = True
                    return
                case consts.RELEASE_CC:
                    for e in self._envelopes:
                        e.updateParameters(release=message.value)
                    self._needs_redraw = True
                    return
                case consts.WAVE_CC:
                    type = int(3 * message.value / consts.MAX_MIDI)
                    match type:
                        case 0: # Sine
                            if self._wave_type != "Sine":
                                self._osc = self._sin
                                self._wave_type = "Sine"
                        case 1: # Saw
                            if self._wave_type != "Saw":
                                self._osc = self._saw
                                self._wave_type = "Saw"
                        case 2: # Square
                            if self._wave_type != "Square":
                                self._osc = self._sqr
                                self._wave_type = "Square"
                    self._needs_redraw = True
                    return
                case consts.CUTOFF_CC | consts.Q_CC:
                    self._Parameter_Interface.handle_cc_message(message.control, message.value)
                    self._needs_redraw = True
                    return
                case consts.REVERB_CC:
                    self._reverb.updateDryWet(message.value / consts.MAX_MIDI) 
                    return
            return

    #Voice management
    def addVoice(self, new_voice: int = 0):
        #Only allow valid voices
        if new_voice < 21 or new_voice > 108:
            if self._debug_mode > 0:
                print("Invalid voice value, no new voice added")
            return
        
        # First check for duplicate voices:
        for i in range(consts.MAX_VOICES):
            if self._voices[i] == new_voice:
                self._envelopes[i].reset()
                self._envelopes[i].start()
                if self._debug_mode == 2:
                    print(f"Retriggering voice {new_voice} at index {i}")
                return

        # Next find UNUSED voices
        for i in range(consts.MAX_VOICES):
            if self._voices[i] == UNUSED:
                self._envelopes[i].start()
                self._voices[i] = new_voice
                return
            
        # If no duplicate or UNUSED voices, then find the oldest released voice
        oldest = 0
        for i in range(1, consts.MAX_VOICES):
            if self._envelopes[i].isOff() and not self._envelopes[oldest].isOff():
                oldest = i
        if self._envelopes[oldest].isOff():
            self._voices[oldest] = new_voice
            self._envelopes[oldest].reset()
            self._envelopes[oldest].start()
            if self._debug_mode == 1 or self._debug_mode == 2:
                print(f"Replaced oldest unused voice at index {oldest}")
            return
        
        # If all voices are busy, then replace the quietest one with the new note
        quietest = 0
        for i in range(1, consts.MAX_VOICES):
            if self._envelopes[i]._value < self._envelopes[quietest]._value:
                quietest = i
        self._voices[quietest] = new_voice
        self._envelopes[quietest].reset()
        self._envelopes[quietest].start()
        if self._debug_mode == 1 or self._debug_mode == 2:
            print(f"Stole voice from index {quietest}")
        return
    def releaseVoice(self, rel_voice: int = 0):
        
        #Only allow valid voices
        if rel_voice < 21 or rel_voice > 108:
            if self._debug_mode > 0:
                print("Invalid voice value, no voice removed")
            return
        
        #Find location for old voice, if it exists
        i = 0
        while self._voices[i] != rel_voice and i < consts.MAX_VOICES - 1:
            i += 1
        if i >= consts.MAX_VOICES:
            if self._debug_mode > 0:
                print("Voice was not active, nothing to release")
            return
        
        if self._debug_mode == 2:
            print("Voice before release: ", self._voices[i])

        #Turn envelope to release phase
        self._envelopes[i].release()

        if self._debug_mode == 2:
            print("Voice after release: ", self._voices[i])
        return
    def pruneVoices(self):
        for i in range(consts.MAX_VOICES):
            if self._voices[i] != UNUSED and self._envelopes[i].isOff():
                self._voices[i] = UNUSED
   
    #Consolidate audio from wavetable and voice list to a buffer for output
    def getAudioBuffer(self):
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)
    
        #Mix all active voices
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]).astype(np.float64) / consts.MAX_VOICES
        
        #Apply reverb
        reverb_buffer = self._reverb.use(mixed_buffer)

        return reverb_buffer
    def get2PoleFilterAudioBuffer(self):
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)
    
        #Mix all active voices
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]).astype(np.float64) / consts.MAX_VOICES
                
        #Update cutoff and resonance if user has changed them
        if self._Parameter_Interface._new_cutoff is not None:
            new_cutoff = self._Parameter_Interface._new_cutoff
            self._Parameter_Interface._new_cutoff = None
            self._filter1_left.setCutoff(new_cutoff)
            self._filter1_right.setCutoff(new_cutoff)
        if self._Parameter_Interface._new_Q is not None:
            new_Q = self._Parameter_Interface._new_Q
            self._Parameter_Interface._new_Q = None
            self._filter1_left.setQ(new_Q)
            self._filter1_right.setQ(new_Q)

        #Apply reverb
        reverb_buffer = self._reverb.use(mixed_buffer)

        #Only use a single filter
        filtered_buffer_left = self._filter1_left.use(reverb_buffer[:, 0])
        filtered_buffer_right = self._filter1_right.use(reverb_buffer[:, 1])

        return np.column_stack([filtered_buffer_left, filtered_buffer_right])
    def get4PoleFilterAudioBuffer(self):
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)

        #Mix all active voices
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]).astype(np.float64) / consts.MAX_VOICES
                 
        #Update cutoff and resonance if user has changed them
        if self._Parameter_Interface._new_cutoff is not None:
            new_cutoff = self._Parameter_Interface._new_cutoff
            self._Parameter_Interface._new_cutoff = None
            self._filter1_left.setCutoff(new_cutoff)
            self._filter1_right.setCutoff(new_cutoff)
            self._filter2.setCutoff(new_cutoff)
        if self._Parameter_Interface._new_Q is not None:
            new_Q = self._Parameter_Interface._new_Q
            self._Parameter_Interface._new_Q = None
            self._filter1_left.setQ(new_Q)
            self._filter1_right.setQ(new_Q)
            self._filter2.setQ(new_Q)

        #Casecade filters
        filtered_buffer = self._filter2.use(self._filter1_left.use(mixed_buffer))

        #Apply reverb
        reverb_buffer = self._reverb.use(filtered_buffer)

        return reverb_buffer
    def getDebugAudioBuffer(self):

        start = time.perf_counter()
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)
            
        #Mix all active voices
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]).astype(np.float64) / consts.MAX_VOICES

        #Apply reverb
        reverb_buffer = self._reverb.use(mixed_buffer) 
        
        ms = (time.perf_counter() - start)*1000
        if ms > consts.TOO_SLOW:
            print(f"SLOW BUFFER GENERATION: {ms:.2f}ms")

        return reverb_buffer
    def getDebug2PoleFilterAudioBuffer(self):

        start = time.perf_counter()
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)
            
        #Mix all active voices
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]).astype(np.float64) / consts.MAX_VOICES


        #Update cutoff and resonance if user has changed them
        if self._Parameter_Interface._new_cutoff is not None:
            new_cutoff = self._Parameter_Interface._new_cutoff
            self._Parameter_Interface._new_cutoff = None
            self._filter1_left.setCutoff(new_cutoff)
            self._filter1_right.setCutoff(new_cutoff)
        if self._Parameter_Interface._new_Q is not None:
            new_Q = self._Parameter_Interface._new_Q
            self._Parameter_Interface._new_Q = None
            self._filter1_left.setQ(new_Q)
            self._filter1_right.setQ(new_Q)

        
        #Apply reverb
        reverb_buffer = self._reverb.use(mixed_buffer)

        #Only use a single filter
        filtered_buffer_left = self._filter1_left.use(reverb_buffer[:, 0])
        filtered_buffer_right = self._filter1_right.use(reverb_buffer[:, 1])

        ms = (time.perf_counter() - start)*1000
        if ms >  consts.TOO_SLOW:
            print(f"SLOW BUFFER GENERATION: {ms:.2f}ms")

        return np.column_stack([filtered_buffer_left, filtered_buffer_right])
    def getDebug4PoleFilterAudioBuffer(self):

        start = time.perf_counter()
            
        #Ensure finished voices are set as such
        self.pruneVoices()

        #Start with silence
        mixed_buffer = np.zeros(consts.BUFFER_SIZE, np.float64)
    
        #Mix all active voices
        voice_env_start = time.perf_counter()
        for i in range(len(self._voices)):
            if self._voices[i] != UNUSED:
                mixed_buffer += self._envelopes[i].applyEnvelope(self._osc[self._voices[i]]) / consts.MAX_VOICES
        voice_env_time = (time.perf_counter() - voice_env_start) * 1000

        #Update cutoff and resonance if user has changed them
        filter_param_start = time.perf_counter()
        if self._Parameter_Interface._new_cutoff is not None:
            new_cutoff = self._Parameter_Interface._new_cutoff
            self._Parameter_Interface._new_cutoff = None
            self._filter1_left.setCutoff(new_cutoff)
            self._filter1_right.setCutoff(new_cutoff)
            self._filter2.setCutoff(new_cutoff)
        if self._Parameter_Interface._new_Q is not None:
            new_Q = self._Parameter_Interface._new_Q
            self._Parameter_Interface._new_Q = None
            self._filter1_left.setQ(new_Q)
            self._filter1_right.setQ(new_Q)
            self._filter2.setCutoff(new_cutoff)
        filter_param_time = (time.perf_counter() - filter_param_start) * 1000

        #Casecade filters
        filter_start = time.perf_counter()
        filtered_buffer = self._filter2.use(self._filter1_left.use(mixed_buffer))
        filter_time = (time.perf_counter() - filter_start) * 1000

        #Apply reverb
        reverb_start = time.perf_counter()
        reverb_buffer = self._reverb.use(filtered_buffer)
        reverb_time = (time.perf_counter() - reverb_start) * 1000

        ms = (time.perf_counter() - start)*1000
        if ms > consts.TOO_SLOW:
            print(f"SLOW BUFFER GENERATION: {ms:.2f}ms")
            if voice_env_time > 1.0:
                print(f"Voice mixing & envelope application time: {voice_env_time:.2f}ms")
            if filter_param_time > 1.0:
                print(f"Filter param processing: {filter_param_time:.2f}ms")
            if filter_time > 1.0:
                print(f"Filter processing: {filter_time:.2f}ms")
            if reverb_time > 1.0:
                print(f"Filter processing: {reverb_time:.2f}ms")

        return reverb_buffer
    
    #Notes that parameters have changed since last update
    def redraw(self):
        self._needs_redraw = False
    def needsRedraw(self) -> bool:
        return self._needs_redraw