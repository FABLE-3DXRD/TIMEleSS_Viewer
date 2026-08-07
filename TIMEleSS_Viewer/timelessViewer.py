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
import fabio.edfimage
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

def save_mean():
    """
    The user wants to save a mean image, let's go for it
    """
    global rawdata
    datatmp = numpy.mean(rawdata, axis=0)
    im = fabio.edfimage.EdfImage(data=datatmp)
    options = qt.QFileDialog.Options()
    fileName, _ = qt.QFileDialog.getSaveFileName(None, "Name of mean image file", "", "EDF files (*.edf);;Tiff files (*.tif);;All files (*.*)", options=options)
    if fileName:
        test, file_extension = os.path.splitext(fileName)
        file_extension =  file_extension.lower()
        if ((file_extension == ".tif") or (file_extension == ".tiff")):
            im.convert("tif").save(fileName)
        elif (file_extension == ".edf"):
            im.save(fileName)
        else:
            msg = qt.QMessageBox()
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("File format not supported : %s" % file_extension)
            msg.setWindowTitle("Error")
            msg.exec_()
            print("Error : file format not supported : %s" % file_extension)

def save_median():
    """
    The user wants to save a median image, let's go for it
    """
    global rawdata
    datatmp = numpy.median(rawdata, axis=0)
    im = fabio.edfimage.EdfImage(data=datatmp)
    options = qt.QFileDialog.Options()
    fileName, _ = qt.QFileDialog.getSaveFileName(None, "Name of median image file", "", "EDF files (*.edf);;Tiff files (*.tif);;All files (*.*)", options=options)
    if fileName:
        test, file_extension = os.path.splitext(fileName)
        file_extension =  file_extension.lower()
        if ((file_extension == ".tif") or (file_extension == ".tiff")):
            im.convert("tif").save(fileName)
        elif (file_extension == ".edf"):
            im.save(fileName)
        else:
            msg = qt.QMessageBox()
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("File format not supported : %s" % file_extension)
            msg.setWindowTitle("Error")
            msg.exec_()
            print("Error : file format not supported : %s" % file_extension)


def stack_all_images():
    """
    Called when the user changes whether to stack all images or not

    Reads data and calls for a replot
    """
    global do_stack_action
    global main_pars, rawdata,omega

    if (do_stack_action.isChecked()): # The user wants a stack, we do it here
        main_pars["stackimages"] = True
        # take the mean of all frames
        datatmp = numpy.mean(rawdata, axis=0)
        # subtractbg if needed
        if (do_bg_action.isChecked() and (main_pars["bgfile"] != None)):
            bgim = fabio.open(main_pars["bgfile"])
            fake_3d = [datatmp-bgim.data]
        else:
            fake_3d = [datatmp]
        # Apply flipping
        fake_3d = numpy.asarray(fake_3d)
        fake_3d = image_flipping(fake_3d,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])
        # Set data
        sv.setStack(fake_3d)
        sv.setGraphTitle("Omega stack")
        # Add peaks here (omega filtering is different than for single frames)
        if (main_pars["show_peaks"] and peaks["set"]):
            # Extract the underlying PlotWidget
            plot_widget = sv.getPlotWidget()
            # Remove all "peaks" item
            plot_widget.remove(kind='curve')
            # Add relevant peaks
            omegamin = min(omega)
            omegamax = max(omega)
            # Need to apply the flip matrix to the peak position... Not sure on how to do that.
            # Brutal a stupid solution
            # Create an empy image, will set to 1 when there is a peak
            [dim0, dim1, dim2] = rawdata.shape
            peakpos = numpy.zeros([1,dim1,dim2],dtype=numpy.int8)
            for peak in peaks["peakinfo"] :
                if ((peak[peaks["Min_o"]] <= omegamax) and (omegamin <= peak[peaks["Max_o"]])):
                    cy = numpy.rint(peak[peaks["detz"]]).astype(int)
                    cx = numpy.rint(peak[peaks["dety"]]).astype(int)
                    # print(cx,cy)
                    peakpos[0,cx,cy] = 1
            # Apply image flipping to locate the peaks on flipped images
            peakpos = image_flipping(peakpos,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])
            # Search peaks and plot a circle
            drawpeaks = zip(*numpy.where(peakpos == 1))
            # print(drawpeaks)
            legendindex = 0
            for p,cx,cy in drawpeaks:
                # print(p,cx,cy)
                # print("Found one at %d %d" % (cx, cy))
                # Define geometry
                t = numpy.linspace(0, 2 * numpy.pi, 200)
                x = cy + main_pars["peakcircleradius"] * numpy.cos(t)
                y = cx + main_pars["peakcircleradius"] * numpy.sin(t)
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
            plot_widget = sv.getPlotWidget()
            plot_widget.remove(kind='curve')
    else: # The user does not want to stack images anymore, we redraw_from_raw
        main_pars["stackimages"] = False
        redraw_from_raw()


def changedatafiles():
    """
    Called when the user selects a menu to change the input data files

    Reads data and calls for a replot
    """
    global rawdata, omega
    global do_stack_action

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
            if ("Omega" in im.header):
                omega.append(float(im.header["Omega"]))
            else:
                omega.append(numpy.nan)
        rawdata = numpy.asarray(rawdata)
        if (main_pars["stackimages"]): # Remove the stack option if it is set. We just read a new list of files
            main_pars["stackimages"] = False
            do_stack_action.setChecked(False)
        redraw_from_raw(0)

def redraw_from_raw(selected_frame=0):
    """
    Redraw the dataset from the raw data
    Applies flip matrix
    Subtract background if necessary

    Send frame to display, first frame by default
    """
    global main_pars, rawdata

    # Flip image
    datatmp = image_flipping(rawdata,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])
    # Remove background, if it is set
    if (do_bg_action.isChecked()):
        if (main_pars["bgfile"] != None):
            print("Reading background from %s" % main_pars["bgfile"])
            bgim = fabio.open(main_pars["bgfile"])
            fake_3d_bg = [bgim.data]
            fake_3d_bg = numpy.asarray(fake_3d_bg)
            fake_3d_bg = image_flipping(fake_3d_bg,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])
            data = []
            for frame in datatmp:
                data.append(frame-fake_3d_bg[0,:])
            sv.setStack(data)
            sv.setFrameNumber(selected_frame)
            on_frame_changed(selected_frame)
        else:
            sv.setStack(datatmp)
            sv.setFrameNumber(selected_frame)
            on_frame_changed(selected_frame)
    else:
        sv.setStack(datatmp)
        # Force a replot
        sv.setFrameNumber(selected_frame)
        on_frame_changed(selected_frame)

def set_OMatrix(o11,o12,o21,o22):
    """
    Force change the flip matrix and replot the dataset
    """
    global main_pars
    global sv

    main_pars["o11"] = o11
    main_pars["o12"] = o12
    main_pars["o21"] = o21
    main_pars["o22"] = o22
    redraw_from_raw(sv.getFrameNumber())

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
    """
    Function to read peaks from a file
    """
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
                if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
                    stack_all_images()
                else:
                    # Force a replot
                    on_frame_changed(sv.getFrameNumber())
        else:
            msg = qt.QMessageBox()
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText("File not found : %s" % main_pars["peakfile"])
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
        if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
            stack_all_images()
        else:
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
            if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
                stack_all_images()
            else:
                change_do_bg()

def change_do_bg():
    """
    Called when the user selects a menu to change the peak circle radius
    """
    global main_pars,sv

    if (do_bg_action.isChecked()):
        main_pars["subtractbg"] = True
        if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
            stack_all_images()
        else:
            redraw_from_raw(sv.getFrameNumber())
    else:
        main_pars["subtractbg"] = False
        if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
            stack_all_images()
        else:
            redraw_from_raw(sv.getFrameNumber())

def change_show_peaks():
    """
    Called when the user selects a menu to change the peak circle radius
    """
    global main_pars
    if (do_show_peaks_action.isChecked()):
        main_pars["show_peaks"] = True
        # Force replot
        if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
            stack_all_images()
        else:
            redraw_from_raw(sv.getFrameNumber())
        # print ("Show peaks")
    else:
        main_pars["show_peaks"] = False
        # print ("Do not show peaks")
        # Force replot
        if (main_pars["stackimages"]): # If the user wants a stack, special function to replot
            stack_all_images()
        else:
            redraw_from_raw(sv.getFrameNumber())


def omegaTitle(idx):
    """
    Called by the silx stack view to set the image title when there is a change
    Sends the frame number
    We set a title based on omega value
    """
    return "omega = %.2f degrees" % omega[idx]

def on_frame_changed(frame_index):
    """
    Signal is sent when silx stack view changes frame, sends the frame number
    If peaks should be added, we change the list of peaks based on value of omega
    """
    global main_pars
    global fileName
    global rawdata
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
        # Need to apply the flip matrix to the peak position... Not sure on how to do that.
        # Brutal a stupid solution
        # Create an empy image, will set to 1 when there is a peak
        [dim0, dim1, dim2] = rawdata.shape
        peakpos = numpy.zeros([1,dim1,dim2],dtype=numpy.int8)
        for peak in peaks["peakinfo"] :
            if ((peak[peaks["Min_o"]] <= om) and (om <= peak[peaks["Max_o"]])):
                cy = numpy.rint(peak[peaks["detz"]]).astype(int)
                cx = numpy.rint(peak[peaks["dety"]]).astype(int)
                # print(cx,cy)
                peakpos[0,cx,cy] = 1
        # Apply image flipping to locate the peaks on flipped images
        peakpos = image_flipping(peakpos,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])
        # Search peaks and plot a circle
        drawpeaks = zip(*numpy.where(peakpos == 1))
        # print(drawpeaks)
        for p,cx,cy in drawpeaks:
            # print(p,cx,cy)
            # print("Found one at %d %d" % (cx, cy))
            # Define geometry
            t = numpy.linspace(0, 2 * numpy.pi, 200)
            x = cy + main_pars["peakcircleradius"] * numpy.cos(t)
            y = cx + main_pars["peakcircleradius"] * numpy.sin(t)
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

def image_flipping(data, o11, o12, o21, o22, flipdir='forward'):
    """
    Code copied from that of Fabian at https://github.com/FABLE-3DXRD/fabian/blob/master/Fabian/detector.py
    Call to this function from Fabian adds -1 in front of all components: https://github.com/FABLE-3DXRD/fabian/blob/master/Fabian/appWin.py#L1931
    Not needed here (flipping done when designing UI)

    Transforming image matrix according to the
    detector orientation matrix given the
    output image  matrix will have coordinates (dety,detz)
    as defined in
    "3DXRD and TotalCryst Geometry - Version 1.0.2" by
    H.F. Poulsen, S. Schmidt, J. Wright, H.O. Sorensen

    Detector_orientation: [[o11,o12],[o21,o22]]

           [[o11,o12],[o21,o22]]
           [[  1,  0],[  0,  1]]  => nothing
           [[ -1,  0],[  0,  1]]  => flipud
           [[  1,  0],[  0, -1]]  => fliplr
           [[ -1,  0],[  0, -1]]  => flipud fliplr

           [[  0,  1],[  1,  0]]  => transpose
           [[  0, -1],[ -1,  0]]  => transpose fliplr flipud
           [[  0, -1],[  1,  0]]  => transpose flipud
           [[  0,  1],[ -1,  0]]  => transpose flipud

    flipdir can takes the values forward or inverse
    forward: raw image -> 3DXRD standard
    inverse: 3DXRD standard -> raw image

    Since we are working with 3D data, axes 0 is the dataset number, then Y and Z directions on detector

    # flipup for 3D data replaced with
    # matrice_retournee = matrice[:,::-1, :]

    # fliplr  for 3D data replaced with
    # matrice_retournee = matrice[:, ::-1]

    # transpose of 3D data replaced with
    np.transpose(a, (0, 2, 1))

    """

    if abs(o11) == 1:
        if (abs(o22) != 1) or (o12 != 0) or (o21 != 0):
            raise ValueError('detector orientation makes no sense 1')
#        img = n.transpose(img) # to get A[i,j] be standard A[dety,detz]
        if o11 == -1:
            # img = n.flipud(img)
            data = data[:,::-1,:]
        if o22 == -1:
            # img = n.fliplr(img)
            data = data[:,:,::-1]
        return data
    if abs(o12) == 1:
        if abs(o21) != 1 or (o11 != 0) or (o22 != 0):
            raise ValueError('detector orientation makes no sense 2')
        #transpose not needed since the matrix is transp from scratch
        data = numpy.transpose(data, (0,2,1)) # make transpose

        if o12 == -1:
            if flipdir == 'forward':
                # img = n.flipud(img)
                data = data[:,::-1,:]
            else:
                #img = n.fliplr(img)
                data = data[:,:,::-1]
        if o21 == -1:
            if flipdir == 'forward':
                # img = n.fliplr(img)
                data = data[:,:,::-1]
            else:
                # img = n.flipud(img)
                data = data[:,::-1,:]
        return data
    raise ValueError('detector orientation makes no sense 3')

def main(argv):
    """
    Main subroutine
    """

    # Global variables with parameters, peaks from peak search info, rawdata, and omega values
    global main_pars,peaks,rawdata,omega
    # Gui elements: main window, on/off menu items to check at other places
    global sv, do_show_peaks_action, do_bg_action, do_stack_action

    qapp = qt.QApplication(sys.argv[1:])

    # Holds information that the Gui needs to know about
    main_pars =  dict()
    main_pars["show_peaks"] = False
    main_pars["peakfile"] = None
    main_pars["peakcircleradius"] = 20
    main_pars["subtractbg"] = False
    main_pars["bgfile"] = None
    main_pars["o11"] = 1
    main_pars["o12"] = 0
    main_pars["o21"] = 0
    main_pars["o22"] = 1
    main_pars["stackimages"] = False

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
        if ("Omega" in im.header):
            omega.append(float(im.header["Omega"]))
        else:
            omega.append(numpy.nan)
    rawdata = numpy.asarray(rawdata)
    #print(rawdata.shape)

    # Starting value for min and max intensity scale, max is quite arbitrary. This should be improved when someone finds time.
    minv = 0
    maxv = max(30,10.*numpy.median(rawdata))

    # Apply flipping matrix
    data = image_flipping(rawdata,main_pars["o11"],main_pars["o12"],main_pars["o21"],main_pars["o22"])

    #for frame in series.frames():
    #    rawdata.append(frame.data)
    #    omega.append(float(frame.header["Omega"]))

    # Prepare a GUI with a stackview from Silx
    sv = StackViewMainWindow()
    sv.setStack(data)
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

    img_orientation_menu = custom_menu.addMenu("Image orientation")
    img_orientation_menu.setDisabled(False)
    # creating QAction Instances
    orientation_action_1001 = qt.QAction("(1,0,0,1)", sv)
    orientation_action_100m1 = qt.QAction("1,0,0,-1)", sv)
    orientation_action_m1001 = qt.QAction("(-1,0,0,1)", sv)
    orientation_action_m100m1 = qt.QAction("-1,0,0,-1)", sv)
    orientation_action_0110 = qt.QAction("(0,1,1,0)", sv)
    orientation_action_01m10 = qt.QAction("(0,1,-1,0)", sv)
    orientation_action_0m110 = qt.QAction("(0,-1,1,0)", sv)
    orientation_action_0m1m10 = qt.QAction("(0,-1,-1,0)", sv)
    # making actions checkable
    orientation_action_1001.setCheckable(True)
    orientation_action_1001.setChecked(True)
    orientation_action_100m1.setCheckable(True)
    orientation_action_m1001.setCheckable(True)
    orientation_action_m100m1.setCheckable(True)
    orientation_action_0110.setCheckable(True)
    orientation_action_01m10.setCheckable(True)
    orientation_action_0m110.setCheckable(True)
    orientation_action_0m1m10.setCheckable(True)
    # adding these actions to the selection menu
    img_orientation_menu.addAction(orientation_action_1001)
    img_orientation_menu.addAction(orientation_action_100m1)
    img_orientation_menu.addAction(orientation_action_m1001)
    img_orientation_menu.addAction(orientation_action_m100m1)
    img_orientation_menu.addAction(orientation_action_0110)
    img_orientation_menu.addAction(orientation_action_01m10)
    img_orientation_menu.addAction(orientation_action_0m110)
    img_orientation_menu.addAction(orientation_action_0m1m10)
    # creating a action group
    action_group = qt.QActionGroup(sv)
    # adding these action to the action group
    action_group.addAction(orientation_action_1001)
    action_group.addAction(orientation_action_100m1)
    action_group.addAction(orientation_action_m1001)
    action_group.addAction(orientation_action_m100m1)
    action_group.addAction(orientation_action_0110)
    action_group.addAction(orientation_action_01m10)
    action_group.addAction(orientation_action_0m110)
    action_group.addAction(orientation_action_0m1m10)
    # Actions for each
    orientation_action_1001.triggered.connect(lambda checked: set_OMatrix(1,0,0,1))
    orientation_action_100m1.triggered.connect(lambda checked: set_OMatrix(1,0,0,-1))
    orientation_action_m1001.triggered.connect(lambda checked: set_OMatrix(-1,0,0,1))
    orientation_action_m100m1.triggered.connect(lambda checked: set_OMatrix(-1,0,0,-1))
    orientation_action_0110.triggered.connect(lambda checked: set_OMatrix(0,1,1,0))
    orientation_action_01m10.triggered.connect(lambda checked: set_OMatrix(0,1,-1,0))
    orientation_action_0m110.triggered.connect(lambda checked: set_OMatrix(0,-1,1,0))
    orientation_action_0m1m10.triggered.connect(lambda checked: set_OMatrix(0,-1,-1,0))

    custom_menu.addSeparator()
    do_stack_action = qt.QAction("Stack all images", sv)
    do_stack_action.setCheckable(True)
    do_stack_action.setChecked(False)
    do_stack_action.triggered.connect(stack_all_images)
    custom_menu.addAction(do_stack_action)

    custom_menu.addSeparator()
    save_mean_action = qt.QAction("Save a mean image", sv)
    save_mean_action.triggered.connect(save_mean)
    custom_menu.addAction(save_mean_action)

    save_median_action = qt.QAction("Save a median image", sv)
    save_median_action.triggered.connect(save_median)
    custom_menu.addAction(save_median_action)

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
