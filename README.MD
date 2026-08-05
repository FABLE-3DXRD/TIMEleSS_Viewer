
# TIMEleSS Viewer

2026, Sébastien Merkel
sebastien.merkel@univ-lille.fr

Simple application to view series of 3D-XRD data files

Meant as replacement for the features we used in Fabian, which is getting old and should be phased out

Can
 - plot series of EDF files with omega values
 - overlay peaks from a peak search
 - subtract a background (from a median image, for instance)

Image orientation remains to be implemented

Built on top of silx, from the Data Analysis Unit, European Synchrotron Radiation Facility, Grenoble

TIMEleSS tools, and the strategy for processing multigrain diffraction data is fully described in an online manual at http://multigrain.texture.rocks/

TIMEleSS tools are open-source, under the terms of the GNU GENERAL PUBLIC LICENSE, Version 2

Information on the ANR-DFG TIMEleSS project: http://timeless.texture.rocks/

Descriptions of TIMEleSS-tools: http://multigrain.texture.rocks/

## Installation instructions

Create and activate a virtual python environements dedicated to 3D-XRD
	A virtual environment in Python is an isolated environment on your computer, where you can run and test your Python projects, without interfering with the main python installation
	See instructions at https://www.w3schools.com/python/python_virtualenv.asp and many other places online

Install required libraries
	pip install fabio
	pip install silx
	pip install numpy

Download the TIMEleSS Viewer by typing
	git clone https://github.com/FABLE-3DXRD/TIMEleSS_Viewer.git

Move into the TIMEleSS_Viewer project
	cd TIMEleSS_Viewer

Build the project
	pip install .

To upgrade a previous install
	move into the folder where you downloaded the TIMEleSS Viewer, and then
	git pull
	pip install --upgrade  --no-deps --force-reinstall

Good luck!

## Usage instructions

Type "timelessViewer" in the command line

Hold the control key and select the first EDF file you want to plot
Hold the shift key and select the last EDF file

The GUI should come up

The GUI has all the usual silx interface

Specific 3D-XRD functions are in the "3D-XRD extra" menu

