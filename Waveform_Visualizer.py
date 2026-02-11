import matplotlib.pyplot as plt
import numpy as np
from lib import consts

# Handles display for visualizations of wave shape, envelope, etc...
class Plot():
    
    def __init__(self, num_plots=consts.NUM_GRAPHS):
        plt.ion()
        self._fig, self._axes = plt.subplots(num_plots, 1, figsize=(10, 8))
        if num_plots == 1:
            self._axes = [self._axes]
            
        self._axes[consts.WAVEFORM_PLOT].set_title('Waveform')
        self._axes[consts.ADSR_PLOT].set_title('Envelope')
        self._axes[consts.FILTER_PLOT].set_title('Filter Response')
            
        # Initialize with empty plots
        for ax in self._axes:
            ax.grid(True, alpha=0.3)
            
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(0.01)  # Force initial draw
        
    def update_plot(self, plot_index, y_data, x_data=None):
        if plot_index >= len(self._axes):
            print(f"Invalid plot_index {plot_index}, only have {len(self._axes)} plots")
            return
            
        if x_data is None:
            x_data = np.arange(len(y_data))
            
        # Store the title before clearing
        ax = self._axes[plot_index]
        current_title = ax.get_title()
        
        # Clear and redraw
        ax.clear()
        ax.plot(x_data, y_data, color='black', linewidth=2)
        
        # Restore styling
        ax.set_title(current_title)
        ax.grid(True, alpha=0.3)
        
        # Force redraw
        self._fig.canvas.draw()
        plt.pause(0.001)  # Minimal pause to ensure draw completes
        
    def close(self):
        """Close the visualization"""
        plt.close(self._fig)