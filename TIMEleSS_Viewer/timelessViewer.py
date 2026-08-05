#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
This is part of the TIMEleSS tools
http://timeless.texture.rocks/

Copyright (C) S. Merkel, Universite de Lille, France

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import fabio
import os
import os.path
import sys
import numpy
from silx.gui.plot.StackView import StackViewMainWindow
from silx.gui import qt  # Import Qt binding and do some set-up
from silx.gui.plot.items.roi import CircleROI

def showAboutWindow():
    dlg =  qt.QMessageBox(sv)
    dlg.setWindowTitle("About the TIMEleSS data viewer...")
    dlg.setText("Simple application to view series of 3D-XRD data files\nMeant as replacement for Fabian\n\nYou can also plot peaks from a peak search and remove a background (from a median image, for instance)\nImage orientation remains to be implemented\n\nBuilt on top of silx, from the Data Analysis Unit, European Synchrotron Radiation Facility, Grenoble\n\nThis code is part of the TIMEleSS tools, available at https://github.com/FABLE-3DXRD/TIMEleSS\n\n(c) 2026 S. Merkel, Univ. Lille, France")
    #dlg.setTextInteractionFlags(qt.TextEditable)
    button = dlg.exec()
    if button == qt.QMessageBox.Ok:
        print("OK!")


def changedatafiles():
    """
    Called when the user selects a menu to change the input data files
    """
    global main_pars, rawdata, omega

    filenames, _ = qt.QFileDialog.getOpenFileNames(
        None,
        "Select all EDF Files",
        None,
        "EDF Images (*.edf)")
    if filenames:
        print("You selected %d images" % len(filenames))
        # Re-read the raw data
        rawdata = []
        omega = []
        for frame in filenames:
            im = fabio.open(frame)
            rawdata.append(im.data)
            omega.append(float(im.header["Omega"]))
        # Remove background, if it is set
        if (do_bg_action.isChecked()):
            if (main_pars["bgfile"] != None):
                print("Reading background from %s" % main_pars["bgfile"])
                bgim = fabio.open(main_pars["bgfile"])
                data = []
                for frame in rawdata:
                    data.append(frame.data-bgim.data)
                sv.setStack(data)
                on_frame_changed(0)
            else:
                sv.setStack(rawdata)
                on_frame_changed(0)
        else:
            sv.setStack(rawdata)
            # Force a replot
            on_frame_changed(0)

def changepeakfile():
    """
    Called when the user selects a menu to change the peak file
    """
    global main_pars
    print ("The user was to change the peak file")

    options = qt.QFileDialog.Options()
    fileName, _ = qt.QFileDialog.getOpenFileName(None, "Open a peak file", "", "FLT files (*.flt);;All files (*.*)", options=options)
    if fileName:
        main_pars["peakfile"] = fileName
        readpeaks()

def readpeaks():
    global main_pars
    global peaks
    if (main_pars["peakfile"] != None):
        print("Reading peaks from %s" % main_pars["peakfile"])
        if (os.path.isfile(main_pars["peakfile"])):
            # Read peak informations from file
            peaks["peakinfo"] = numpy.genfromtxt(main_pars["peakfile"], skip_header=1)
            # Figure out important columns from header
            infile = open(main_pars["peakfile"], 'r')
            header = (infile.readline().strip('\n'))[1:].split()
            infile.close()
            peaks["dety"] = header.index("sc")
            peaks["detz"] = header.index("fc")
            peaks["Min_o"] = header.index("Min_o")
            peaks["Max_o"] = header.index("Max_o")
            peaks["set"] = True
            if (main_pars["show_peaks"]):
                # Force a replot
                on_frame_changed(sv.getFrameNumber())
        else:
            msg = qt.QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("More file not found : %s" % main_pars["peakfile"])
            msg.setWindowTitle("Error")
            msg.exec_()
            print("Error : file not found : %s" % main_pars["peakfile"])
    # print(header)
    # print(colsc,colfc,Min_o,Max_o)


def changepeakcircleradius():
    """
    Called when the user selects a menu to change the peak circle radius
    """
    global main_pars
    print ("The user was to change the peak circle radius")
    roll, done = qt.QInputDialog.getInt(sv,'Peak circle radius', 'Peak cicle radius (in px):',value = main_pars["peakcircleradius"] )
    if (done):
        main_pars["peakcircleradius"] = roll
        # Force a replot
        on_frame_changed(sv.getFrameNumber())

def changeBgFile():
    """
    Called when the user selects a menu to change the peak file
    """
    global main_pars
    print ("The user was to change the background file")

    options = qt.QFileDialog.Options()
    fileName, _ = qt.QFileDialog.getOpenFileName(None, "Open a background file", "", "EDF files (*.edf);;All files (*.*)", options=options)
    if fileName:
        main_pars["bgfile"] = fileName
        print("Background will be read from %s" % main_pars["bgfile"])
        if (main_pars["subtractbg"] == True):
            change_do_bg()

def change_do_bg():
    """
    Called when the user selects a menu to change the peak circle radius
    """
    global main_pars
    if (do_bg_action.isChecked()):
        main_pars["subtractbg"] = True
        if (main_pars["bgfile"] != None):
            print("Reading background from %s" % main_pars["bgfile"])
            bgim = fabio.open(main_pars["bgfile"])
            data = []
            for frame in rawdata:
                data.append(frame.data-bgim.data)
            sv.setStack(data)
            on_frame_changed(sv.getFrameNumber())
    else:
        main_pars["subtractbg"] = False
        sv.setStack(rawdata)
        on_frame_changed(sv.getFrameNumber())

def change_show_peaks():
    """
    Called when the user selects a menu to change the peak circle radius
    """
    global main_pars
    if (do_show_peaks_action.isChecked()):
        main_pars["show_peaks"] = True
        # Force replot
        on_frame_changed(sv.getFrameNumber())
        # print ("Show peaks")
    else:
        main_pars["show_peaks"] = False
        # print ("Do not show peaks")
        # Force replot
        on_frame_changed(sv.getFrameNumber())


def omegaTitle(idx):
    """
    Called by the silx stack view to set the image title when there is a change
    Sends the frame number
    We set a title based on omega value
    """
    return "w = %.2f" % omega[idx]

def on_frame_changed(frame_index):
    """
    Signal is sent when silx stack view changes frame, sends the frame number
    If peaks should be added, we change the list of peaks based on value of omega
    """
    global main_pars
    global fileName
    #print(f"The active frame has changed to: {frame_index}")
    # Extract the underlying PlotWidget
    plot_widget = sv.getPlotWidget()
    # If we need to add peaks, do so
    if (main_pars["show_peaks"] and peaks["set"]):
        # Remove all "peaks" item
        plot_widget.remove(kind='curve')
        # Add relevant peaks
        om = omega[frame_index]
        legendindex = 0
        for peak in peaks["peakinfo"] :
            if ((peak[peaks["Min_o"]] <= om) and (om <= peak[peaks["Max_o"]])):
                cx, cy  = peak[peaks["detz"]], peak[peaks["dety"]]
                # print("Found one at %d %d" % (cx, cy))
                # Define geometry
                t = numpy.linspace(0, 2 * numpy.pi, 200)
                x = cx + main_pars["peakcircleradius"] * numpy.cos(t)
                y = cy + main_pars["peakcircleradius"] * numpy.sin(t)
                # print(min(x), max(x), min(y), max(y))
                # Add via the native addCurve method
                plot_widget.addCurve(
                    x = x,
                    y = y,
                    color='red',
                    legend = 'peak%d' % legendindex,
                    linestyle='-',
                    linewidth=1
                )
                legendindex += 1
    else:
        # Remove all "peaks" item
        plot_widget.remove(kind='curve')


def main(argv):
    """
    Main subroutine
    """

    # Global variables with parameters, peaks from peak search info, rawdata, and omega values
    global main_pars,peaks,rawdata,omega
    # Gui elements: main window, on/off menu items to check at other places
    global sv, do_show_peaks_action, do_bg_action

    qapp = qt.QApplication(sys.argv[1:])

    # Holds information that the Gui needs to know about
    main_pars =  dict()
    main_pars["show_peaks"] = False
    main_pars["peakfile"] = None
    main_pars["peakcircleradius"] = 20
    main_pars["subtractbg"] = False
    main_pars["bgfile"] = None

    # Holds information on peaks (found with a peak search for instance)
    # Set when reading a peak file
    peaks = dict()
    peaks["peakinfo"] = None
    peaks["set"] = False
    peaks["dety"] = 0
    peaks["detz"] = 0
    peaks["Min_o"] = 0
    peaks["Max_o"] = 0

    # Location of EDF files
    #dialog = qt.QFileDialog()
    #dialog.setFileMode(qt.QFileDialog.FileMode.ExistingFiles)
    #dialog.setNameFilter("EDF Images (*.edf)")
    #if dialog.exec_():
    #    fileNames = dialog.selectedFiles()
    #    print(fileNames)

    filenames, _ = qt.QFileDialog.getOpenFileNames(
        None,
        "Select all EDF Files",
        None,
        "EDF Images (*.edf)")
    if filenames:
        print("You selected %d images" % len(filenames))




    # Read data
    # edf_dir = "/home/smerkel/Projets/2026-CaPv-Su-Zhang/CaPv_XRD_pattern_66GPa_edf"
    # stem  = "BX90M6_1_008_"
    # first = 1
    # last = 96
    # extension = ".edf"
    # digits=5
    # filenames = fabio.file_series.numbered_file_series("%s/%s" % (edf_dir, stem), first, last, extension, digits=digits)
    # print("Number of files: %s" % len(filenames))
    # series = fabio.open_series(filenames)

    # Reading diffraction data from file series
    rawdata = []
    omega = []

    for frame in filenames:
        im = fabio.open(frame)
        rawdata.append(im.data)
        omega.append(float(im.header["Omega"]))

    # Starting value for min and max intensity scale
    minv = 0
    maxv = 10.*numpy.median(rawdata)
    #print(numpy.median(rawdata), numpy.mean(rawdata), numpy.min(rawdata), numpy.max(rawdata))


    #for frame in series.frames():
    #    rawdata.append(frame.data)
    #    omega.append(float(frame.header["Omega"]))

    # Prepare a GUI with a stackview from Silx
    sv = StackViewMainWindow()
    sv.setStack(rawdata)
    sv.setColormap(normalization="arcsinh", vmin=minv, vmax=maxv)
    sv.setKeepDataAspectRatio(True)
    sv.setTitleCallback(omegaTitle) # Set a new title with the value of omega for each image
    sv.sigFrameChanged.connect(on_frame_changed) # Prepare a signal to know when the user changes frame
    sv.setWindowTitle("TIMEleSS Data Viewer")

    # Add additional menu items for 3D-XRD operations
    menu_bar = sv.menuBar()
    custom_menu = menu_bar.addMenu("3D-XRD extra")
    data_action = qt.QAction("Read data from...", sv)
    data_action.triggered.connect(changedatafiles)
    custom_menu.addAction(data_action)
    custom_menu.addSeparator()
    peak_action = qt.QAction("Read peaks from...", sv)
    peak_action.triggered.connect(changepeakfile)
    custom_menu.addAction(peak_action)
    do_show_peaks_action = qt.QAction("Show peaks", sv)
    do_show_peaks_action.setCheckable(True)
    do_show_peaks_action.setChecked(main_pars["show_peaks"])
    do_show_peaks_action.triggered.connect(change_show_peaks)
    custom_menu.addAction(do_show_peaks_action)
    peak_radius_action = qt.QAction("Set peak circle radius", sv)
    peak_radius_action.triggered.connect(changepeakcircleradius)
    custom_menu.addAction(peak_radius_action)
    custom_menu.addSeparator()
    bg_action = qt.QAction("Read background from...", sv)
    bg_action.triggered.connect(changeBgFile)
    custom_menu.addAction(bg_action)
    do_bg_action = qt.QAction("Subtract background", sv)
    do_bg_action.setCheckable(True)
    do_bg_action.triggered.connect(change_do_bg)
    custom_menu.addAction(do_bg_action)
    custom_menu.addSeparator()
    file_orientation_menu = custom_menu.addMenu("Image orientation")
    file_orientation_menu.setDisabled(True)
    # Add about menu item
    about_menu = menu_bar.addMenu("About...")
    about_action = qt.QAction("About the TIMEleSS data viewer...", sv)
    about_action.triggered.connect(showAboutWindow)
    about_menu.addAction(about_action)

    # Have plot orientation identical to that of Fabian
    sv.getPlotWidget().setYAxisInverted(False)
    sv.getPlotWidget().setXAxisInverted(True)

    # Plot!
    sv.show()

    qapp.exec_()


# Calling method 1 (used when generating a binary in setup.py)
def run():
	main(sys.argv[1:])

# Calling method 2 (if run from the command line)
if __name__ == "__main__":
    main(sys.argv[1:])
