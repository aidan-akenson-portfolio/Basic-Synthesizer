import pyaudio
from lib import consts
import numpy as np

#Handles stream open, write, and close functionality
class output:

    #Initialize pyaudio output stream
    def __init__(self, debug_mode: int = consts.DEBUG_MODE):

        self._p = pyaudio.PyAudio()     
        self._stream = None
        self._isPlaying = False
        self._buffer_provider = None
        self._debug_mode = debug_mode #0 --- No debug outputs
                                      #1 --- Simple debug outputs
                                      #2 --- Verbose debug outputs
                                      #3 --- Efficiency debug outputs

        #Check output device
        if self._debug_mode > 0:
            # Print default device info
            default_info = self._p.get_default_output_device_info()
            print(f"Using device: {default_info['name']}")

        self._silence = np.zeros(consts.BUFFER_SIZE, np.int16)

        self.initStream(self._buffer_provider)
        
    #Don't leave the stream open!
    def __del__(self):
        if self._debug_mode > 0:
            print("Destroying output object")
        self.stop()
        self._p.terminate()

    #Initialize stream and callback
    def initStream(self, buffer_provider):
        #Link to the audio created in the synth
        self._buffer_provider = buffer_provider

        # Find Specified API (or just use 0 if nothing was specified)
        api = None if consts.AUDIO_API != '' else 0
        for i in range(self._p.get_host_api_count()):
            api_info = self._p.get_host_api_info_by_index(i)
            if consts.AUDIO_API in api_info['name']:
                api = i
                if self._debug_mode == 1 or self._debug_mode == 2:
                    print(f"Found {api_info.get('name')} API at index: {api}")
                break
         
        # Find your interface/output device (or just use 0 if nothing was specified)
        output_device = None if consts.INTERFACE_NAME != '' else 0
        if api is not None:
            for i in range(self._p.get_device_count()):
                device_info = self._p.get_device_info_by_index(i)
                if (device_info['hostApi'] == api and 
                    device_info['maxOutputChannels'] > 0 and
                    consts.INTERFACE_NAME in device_info['name'].lower()):
                    output_device = i
                    if self._debug_mode == 1 or self._debug_mode == 2:
                        print(f"Selected {device_info.get('name')} at device index: {output_device}")
                    if self._debug_mode == 2:
                        print(f"\nDevice details: {device_info}\n")
                    break

        # Define the callback
        def stream_callback(in_data, frame_count, time_info, status):
            if not self._isPlaying or self._buffer_provider is None:
                return (self._silence.tobytes(), pyaudio.paContinue)
            
            # Get fresh data from the buffer provider
            new_data = (self._buffer_provider() * 32767).astype(np.int16)
            new_data = new_data.flatten()
            
            #if self._debug_mode == 2:
            #    print(f"Callback getting fresh data from provider")
            #    print(f"First few samples: {new_data[:5]}")
            
            return (new_data.tobytes(), pyaudio.paContinue)
        
        # Create the stream
        if self._stream is None:
            self._stream = self._p.open(
                format=pyaudio.paInt16, 
                channels=2,
                rate=consts.BITRATE,
                output=True,
                output_device_index=output_device,
                stream_callback=stream_callback,
                frames_per_buffer=consts.BUFFER_SIZE
            )
            self._stream.start_stream()
            self._isPlaying = True
        
    #Write to output stream using provided buffer
    def play(self, buffer_provider):

        self._buffer_provider = buffer_provider

        #Open new stream (if no others are already open) with callback
        if self._stream is None:
            self.initStream(buffer_provider)
        
        self._isPlaying = True

    #Close stream
    def stop(self):
        self._current_data = self._silence
        #if self._debug_mode > 0:
        #    print("Stopping stream")
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        self._isPlaying = False

    def isPlaying(self) -> bool:
        # Also check if stream is active
        if self._stream is not None and not self._stream.is_active():
            self._isPlaying = False
        return self._isPlaying