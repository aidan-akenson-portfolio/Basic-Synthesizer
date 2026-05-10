=====SETUP=====
 1) Install dependencies

 2) Configure consts.py to recognize your hardware (although autodetection should hopefully handle outputs if set to '')
     - Note that MIDI values for waveshape, filter, and envelope parameters may not be the same on your controller.
     There is no autodetection for this implemented, so you'll have to change that manually. Turning on debug mode can
     quickly show you which channels are being used for your desired input device. 

 3) Run Manager.py


=====FEATURES TO WORK ON=====

 1) Fix displays not working (some matplotlib dependency is broken)
 
 2) Fix reverb being limited by ADSR unintentionally

 3) Improve device autodetection

 4) Make portable
