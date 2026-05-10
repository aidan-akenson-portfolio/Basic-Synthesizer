import Synth
#import Waveform_Visualizer

from lib import consts

import time
import numpy as np

class Manager:
    def __init__(self):
        # Components
        self.synth = Synth.Synth()
        #self.visualizer = Waveform_Visualizer.Plot()

        # Timing
        self._last_vis_update = 0
        self._vis_update_interval = 0.05 # 20 times per second

        # State
        self._is_running = False

    def start(self):
        self._is_running = True
        
        # Main loop
        try:
            while self._is_running:
                #self._update_visualization_if_needed()
                time.sleep(0.016)
        except KeyboardInterrupt:
            pass

        self.shutdown()
    
    def shutdown(self):
        self._is_running = False

        # Stop visualizer
        #if self.visualizer:
        #    self.visualizer.close()


    #================VISUALIZATION================

    def _update_visualization_if_needed(self):
        current_time = time.time()
        if current_time - self._last_vis_update < self._vis_update_interval or not self.synth.needsRedraw():
            return
        try:
            waveform_data = self._generate_waveform_data()

            envelope_data = self._generate_envelope_data()
            filter_data = self._generate_filter_data()
        
            self.visualizer.update_plot(consts.WAVEFORM_PLOT, np.concat((waveform_data, waveform_data)))
            self.visualizer.update_plot(consts.ADSR_PLOT, envelope_data)
            self.visualizer.update_plot(consts.FILTER_PLOT, y_data=filter_data[1], x_data=filter_data[0])

            self.synth.redraw()
            self._last_vis_update = current_time
        except Exception as e:
            print(f"Visualization update error: {e}")

    def _generate_waveform_data(self):
        samples = 1000
        t = np.linspace(0, 2 * np.pi, samples)

        wave_type = self.synth._wave_type
        if wave_type == "Sine":
            return np.sin(t)
        elif wave_type == "Saw":
            return -1 * (1 - (2 * (t / (2 * np.pi)) - 1.0))
        elif wave_type == "Square":
            return np.sign(np.sin(t))
        else:
            raise Exception(ValueError)
        
    def _generate_envelope_data(self):
        return self.synth._envelopes[0].getEnvelopeData()
    
    def _generate_filter_data(self):
        [w, h] = self.synth._filter1.getFreqResponse()
        if consts.POLES == 4:
            np.square(h) # Account for cascaded filters
        return [w, h]


#Runs the synth
if __name__ == "__main__":

    manager = Manager()
    manager.start()