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
# import silx.gui.qt.Qt  # Import Qt binding and do some set-up
from silx.gui.plot.items.roi import CircleROI


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

    if (data.ndim == 2):
        # If the data is 2D, we add a third column at the beginning of the array to fake a 3D dataset so the functions below work
        data = numpy.array([data])
        dataWas2D = True
    else:
        dataWas2D = False

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
        if (dataWas2D):
            return data[0]
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
        if (dataWas2D):
            return data[0]
        return data
    raise ValueError('detector orientation makes no sense 3')



class ClickableLineEdit(qt.QLineEdit):
    """
    Custom line edit with a mouse clicked event
    Took from the web
    https://stackoverflow.com/questions/25560748/add-a-click-on-qlineedit
    """
    clicked = qt.pyqtSignal() # signal when the text entry is left clicked

    def mousePressEvent(self, event):
        if event.button() == qt.Qt.LeftButton: self.clicked.emit()
        else: super().mousePressEvent(event)


class timelessViewer(StackViewMainWindow):
    """
    The timelessViewer is built agains StackViewMainWindow in silx
    StackViewMainWindow brings all the plotting interface of 3D datasets
    We add specifics for 3D XRD


    :param QWidget parent: Parent widget, or None
    """

    def __init__(self, parent=None):
        # Initialize the StackViewMainWindow
        super().__init__(parent)

        # Holds information that the Gui needs to know about
        self.main_pars =  dict()
        self.main_pars["show_peaks"] = False
        self.main_pars["peakfile"] = None
        self.main_pars["peakcircleradius"] = 20
        self.main_pars["subtractbg"] = False
        self.main_pars["bgfile"] = None
        self.main_pars["o11"] = 1   # Flip- or O-matrix
        self.main_pars["o12"] = 0   # Flip- or O-matrix
        self.main_pars["o21"] = 0   # Flip- or O-matrix
        self.main_pars["o22"] = 1   # Flip- or O-matrix
        self.main_pars["stackimages"] = False

        # Holds information on peaks (found with a peak search for instance)
        # Set when reading a peak file
        self.peaks = dict()
        self.peaks["peakinfo"] = None
        self.peaks["set"] = False
        self.peaks["dety"] = 0 # Column with dety
        self.peaks["detz"] = 0 # Column with detz
        self.peaks["Min_o"] = 0 # Column with Min_omega
        self.peaks["Max_o"] = 0 # Column with Max_omega

        # try to load a first set of data
        filenames, _ = qt.QFileDialog.getOpenFileNames(
            None,
            "Select all EDF Files",
            None,
            "EDF Images (*.edf)")

        # Reading diffraction data from file series and setting the corresponding data
        rawdata = []
        self.omega = []
        for frame in filenames:
            im = fabio.open(frame)
            rawdata.append(im.data)
            if ("Omega" in im.header):
                self.omega.append(float(im.header["Omega"]))
            else:
                self.omega.append(numpy.nan)
        self.rawdata = numpy.asarray(rawdata)

        # Call a dedicated funtion to build the UI
        self.buildUI()


    def buildUI(self):
        """
        Called to build the user interface

        Object variables:
         - self.sv : the main stackview window
         - self.do_bg_action: check box to know if background should be removed
         - self.do_show_peaks_action: check box to know whether peaks should be shown or not
         - self.qeditbg: entry with the name of the bg file
         - self.qeditpeaks: entry with the name of the peak file
         - self.do_stack_action: check box to know if frames should be stacked in omega

        """

        # Starting value for min and max intensity scale, max is quite arbitrary. This should be improved when someone finds time.
        minv = 0
        maxv = max(30,10.*numpy.median(self.rawdata))

        # Apply flipping matrix
        data = image_flipping(self.rawdata,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])

        # Prepare a GUI with a stackview from Silx
        self.sv = StackViewMainWindow()
        if (data.size > 0):
            self.sv.setStack(data)
        self.sv.setColormap(normalization="arcsinh", vmin=minv, vmax=maxv)
        self.sv.setKeepDataAspectRatio(True)
        self.sv.setTitleCallback(self.omegaTitle) # Set a new title with the value of omega for each image
        self.sv.sigFrameChanged.connect(self.on_frame_changed) # Prepare a signal to know when the user changes frame
        self.sv.setWindowTitle("TIMEleSS Data Viewer")

        # Add additional menu items for 3D-XRD operations
        menu_bar = self.sv.menuBar()
        custom_menu = menu_bar.addMenu("3D-XRD extra")

        # Change data files
        data_action = qt.QAction("Read data from...", self.sv)
        data_action.triggered.connect(self.changedatafiles)
        custom_menu.addAction(data_action)

        # Peaks
        custom_menu.addSeparator()
        peak_action = qt.QAction("Read peaks from...", self.sv)
        peak_action.triggered.connect(self.changepeakfile)
        custom_menu.addAction(peak_action)
        self.do_show_peaks_action = qt.QAction("Show peaks", self.sv)
        self.do_show_peaks_action.setCheckable(True)
        self.do_show_peaks_action.setChecked(self.main_pars["show_peaks"])
        self.do_show_peaks_action.triggered.connect(self.change_show_peaks)
        custom_menu.addAction(self.do_show_peaks_action)
        peak_radius_action = qt.QAction("Set peak circle radius", self.sv)
        peak_radius_action.triggered.connect(self.changepeakcircleradius)
        custom_menu.addAction(peak_radius_action)

        # Background
        custom_menu.addSeparator()
        bg_action = qt.QAction("Read background from...", self.sv)
        bg_action.triggered.connect(self.changeBgFile)
        custom_menu.addAction(bg_action)
        self.do_bg_action = qt.QAction("Subtract background", self.sv)
        self.do_bg_action.setCheckable(True)
        self.do_bg_action.triggered.connect(self.change_do_bg)
        custom_menu.addAction(self.do_bg_action)

        # Image flipping
        custom_menu.addSeparator()
        img_orientation_menu = custom_menu.addMenu("Image orientation")
        img_orientation_menu.setDisabled(False)
        orientation_action_1001 = qt.QAction("(1,0,0,1)", self.sv)
        orientation_action_100m1 = qt.QAction("1,0,0,-1)", self.sv)
        orientation_action_m1001 = qt.QAction("(-1,0,0,1)", self.sv)
        orientation_action_m100m1 = qt.QAction("-1,0,0,-1)", self.sv)
        orientation_action_0110 = qt.QAction("(0,1,1,0)", self.sv)
        orientation_action_01m10 = qt.QAction("(0,1,-1,0)", self.sv)
        orientation_action_0m110 = qt.QAction("(0,-1,1,0)", self.sv)
        orientation_action_0m1m10 = qt.QAction("(0,-1,-1,0)", self.sv)
        orientation_action_1001.setCheckable(True)
        orientation_action_1001.setChecked(True)
        orientation_action_100m1.setCheckable(True)
        orientation_action_m1001.setCheckable(True)
        orientation_action_m100m1.setCheckable(True)
        orientation_action_0110.setCheckable(True)
        orientation_action_01m10.setCheckable(True)
        orientation_action_0m110.setCheckable(True)
        orientation_action_0m1m10.setCheckable(True)
        img_orientation_menu.addAction(orientation_action_1001)
        img_orientation_menu.addAction(orientation_action_100m1)
        img_orientation_menu.addAction(orientation_action_m1001)
        img_orientation_menu.addAction(orientation_action_m100m1)
        img_orientation_menu.addAction(orientation_action_0110)
        img_orientation_menu.addAction(orientation_action_01m10)
        img_orientation_menu.addAction(orientation_action_0m110)
        img_orientation_menu.addAction(orientation_action_0m1m10)
        action_group = qt.QActionGroup(self.sv)  # Grouping the orientation menus into one group, so only one is selected
        action_group.addAction(orientation_action_1001)
        action_group.addAction(orientation_action_100m1)
        action_group.addAction(orientation_action_m1001)
        action_group.addAction(orientation_action_m100m1)
        action_group.addAction(orientation_action_0110)
        action_group.addAction(orientation_action_01m10)
        action_group.addAction(orientation_action_0m110)
        action_group.addAction(orientation_action_0m1m10)
        # Actions for each
        orientation_action_1001.triggered.connect(lambda checked: self.set_OMatrix(1,0,0,1))
        orientation_action_100m1.triggered.connect(lambda checked: self.set_OMatrix(1,0,0,-1))
        orientation_action_m1001.triggered.connect(lambda checked: self.set_OMatrix(-1,0,0,1))
        orientation_action_m100m1.triggered.connect(lambda checked: self.set_OMatrix(-1,0,0,-1))
        orientation_action_0110.triggered.connect(lambda checked: self.set_OMatrix(0,1,1,0))
        orientation_action_01m10.triggered.connect(lambda checked: self.set_OMatrix(0,1,-1,0))
        orientation_action_0m110.triggered.connect(lambda checked: self.set_OMatrix(0,-1,1,0))
        orientation_action_0m1m10.triggered.connect(lambda checked: self.set_OMatrix(0,-1,-1,0))

        # Stack images
        custom_menu.addSeparator()
        self.do_stack_action = qt.QAction("Stack all images", self.sv)
        self.do_stack_action.setCheckable(True)
        self.do_stack_action.setChecked(False)
        self.do_stack_action.triggered.connect(self.stack_all_images)
        custom_menu.addAction(self.do_stack_action)

        # Save a mean or a median
        custom_menu.addSeparator()
        save_mean_action = qt.QAction("Save a mean image", self.sv)
        save_mean_action.triggered.connect(self.save_mean)
        custom_menu.addAction(save_mean_action)
        save_median_action = qt.QAction("Save a median image", self.sv)
        save_median_action.triggered.connect(self.save_median)
        custom_menu.addAction(save_median_action)

        # Add about menu item
        about_menu = menu_bar.addMenu("About...")
        about_action = qt.QAction("About the TIMEleSS data viewer...", self.sv)
        about_action.triggered.connect(self.showAboutWindow)
        about_menu.addAction(about_action)

        # Have plot orientation identical to that of Fabian
        self.sv.getPlotWidget().setYAxisInverted(False)
        self.sv.getPlotWidget().setXAxisInverted(True)

        # Add labels to inform user of peak and background files
        svwidget = self.sv.centralWidget()
        svlayout = svwidget.layout()

        gridLayout = qt.QGridLayout()
        gridLayout.setSpacing(5)
        gridLayout.setContentsMargins(0, 0, 0, 0)
        qlabel1 = qt.QLabel(self.sv)
        qlabel1.setText("Background file : ")
        gridLayout.addWidget(qlabel1, 0, 0)
        qlabel2 = qt.QLabel(self.sv)
        qlabel2.setText("Peak file : ")
        gridLayout.addWidget(qlabel2, 0, 2)
        self.qeditbg = ClickableLineEdit(self.sv)
        self.qeditbg.setText("None")
        self.qeditbg.setReadOnly(True)
        self.qeditbg.clicked.connect(self.changeBgFile)
        gridLayout.addWidget(self.qeditbg, 0, 1)
        # bgApplied = qt.QCheckBox("Applied", sv)
        # bgApplied.stateChanged.connect(change_do_bg)
        # gridLayout.addWidget(bgApplied, 0, 2)
        self.qeditpeaks = ClickableLineEdit(self.sv)
        self.qeditpeaks.setText("None")
        self.qeditpeaks.setReadOnly(True)
        self.qeditpeaks.clicked.connect(self.changepeakfile)
        gridLayout.addWidget(self.qeditpeaks, 0, 3)
        # showPeaks = qt.QCheckBox("Show peaks", sv)
        # showPeaks.stateChanged.connect(change_show_peaks)
        # gridLayout.addWidget(showPeaks, 1, 2)
        gridLayout.setColumnStretch(1, 2)
        gridLayout.setColumnStretch(3, 2)
        svlayout.addLayout(gridLayout,svlayout.rowCount(),-1)

        # Plot!
        self.sv.show()

    def omegaTitle(self,idx):
        """
        Called by the silx stack view to set the image title when there is a change
        Sends the frame number
        We set a title based on omega value
        """

        if (len(self.omega) > idx):
            return "omega = %.2f degrees" % self.omega[idx]
        else:
            return "No omega defined"


    def on_frame_changed(self,frame_index):
        """
        Signal is sent when silx stack view changes frame, sends the frame number

        If peaks should be added, we change the list of peaks based on value of omega
        """
        global main_pars
        global fileName
        global rawdata
        #print(f"The active frame has changed to: {frame_index}")
        # Extract the underlying PlotWidget
        plot_widget = self.sv.getPlotWidget()
        # If we need to add peaks, do so
        if (self.main_pars["show_peaks"] and self.peaks["set"]):
            # Remove all "peaks" item
            plot_widget.remove(kind='curve')
            # Add relevant peaks, at the omega value we are at
            om = self.omega[frame_index]
            legendindex = 0
            # Need to apply the flip matrix to the peak position... Not sure on how to do that.
            # Brutal a stupid solution
            # Create an empy image, will set to 1 when there is a peak
            [dim0, dim1, dim2] = self.rawdata.shape
            peakpos = numpy.zeros([1,dim1,dim2],dtype=numpy.int8)
            for peak in self.peaks["peakinfo"] :
                if ((peak[self.peaks["Min_o"]] <= om) and (om <= peak[self.peaks["Max_o"]])):
                    cy = numpy.rint(peak[self.peaks["detz"]]).astype(int)
                    cx = numpy.rint(peak[self.peaks["dety"]]).astype(int)
                    # print(cx,cy)
                    peakpos[0,cx,cy] = 1
            # Apply image flipping to locate the peaks on flipped images
            peakpos = image_flipping(peakpos,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])
            # Search peaks and plot a circle
            drawpeaks = zip(*numpy.where(peakpos == 1))
            # Draw a circle around each peak position
            for p,cx,cy in drawpeaks:
                t = numpy.linspace(0, 2 * numpy.pi, 200)
                x = cy + self.main_pars["peakcircleradius"] * numpy.cos(t)
                y = cx + self.main_pars["peakcircleradius"] * numpy.sin(t)
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


    def showAboutWindow(self):
        dlg =  qt.QMessageBox(self.sv)
        dlg.setWindowTitle("About the TIMEleSS data viewer...")
        dlg.setText("TIMEleSS data viewer\nSimple application to view series of 3D-XRD data files\n(c) 2026 S. Merkel, Univ. Lille, France")
        dlg.setIcon(qt.QMessageBox.Information)
        dlg.setTextInteractionFlags(qt.Qt.TextEditable)
        dlg.setDetailedText("""Features (all accessible from the 3D-XRD extra menu)
 - plot series of EDF files with omega values
 - overlay peaks from a peak search
 - subtract a background (from a median image, for instance)
 - play with image orientation and the flip matrix (O-matrix) options
 - stack all images
 - save a mean image
  -save a median image
Could be also updated to deal with HDF5 files. Will come at some point.

The TIMEleSS data viewer is built on top of silx, from the Data Analysis Unit, European Synchrotron Radiation Facility, Grenoble, and described at https://www.silx.org/

Homepage : https://github.com/FABLE-3DXRD/TIMEleSS_Viewer

TIMEleSS-tools, and the strategy for processing multigrain diffraction data is fully described in an online manual at http://multigrain.texture.rocks/

TIMEleSS-tools and the TIMEleSS data viewer are open-source, under the terms of the GNU GENERAL PUBLIC LICENSE, Version 2""")
        button = dlg.exec()
        #if button == qt.QMessageBox.Ok:
        #    print("OK!")


    def set_OMatrix(self,o11,o12,o21,o22):
        """
        Force change the flip matrix and replot the dataset

        :param o elements: elements of the flip matrix
        """
        global main_pars
        global sv

        self.main_pars["o11"] = o11
        self.main_pars["o12"] = o12
        self.main_pars["o21"] = o21
        self.main_pars["o22"] = o22
        self.redraw_from_raw(self.sv.getFrameNumber())

    def redraw_from_raw(self,selected_frame=0):
        """
        Redraw the dataset from the raw data
        Applies flip matrix
        Subtract background if necessary

        :param int selected_frame: frame to display, first frame by default
        """

        # Flip image
        datatmp = image_flipping(self.rawdata,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])
        # Remove background, if it is set
        if (self.do_bg_action.isChecked()):
            if (self.main_pars["bgfile"] != None):
                # print("Reading background from %s" % main_pars["bgfile"])
                bgim = fabio.open(self.main_pars["bgfile"])
                bgim = image_flipping(bgim.data,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])
                data = []
                for frame in datatmp:
                    data.append(frame-bgim)
                self.sv.setStack(data)
                self.sv.setFrameNumber(selected_frame)
                self.on_frame_changed(selected_frame)
            else:
                self.sv.setStack(datatmp)
                self.sv.setFrameNumber(selected_frame)
                self.on_frame_changed(selected_frame)
        else:
            self.sv.setStack(datatmp)
            # Force a replot
            self.sv.setFrameNumber(selected_frame)
            self.on_frame_changed(selected_frame)


    def changeBgFile(self):
        """
        Called when the user selects a menu to change the background file
        """

        # print ("The user was to change the background file")

        options = qt.QFileDialog.Options()
        fileName, _ = qt.QFileDialog.getOpenFileName(None, "Open a background file", "", "EDF files (*.edf);;All files (*.*)", options=options)
        if fileName:
            self.main_pars["bgfile"] = fileName
            # print("Background will be read from %s" % main_pars["bgfile"])
            self.qeditbg.setText(os.path.split(self.main_pars["bgfile"])[1])
            if (self.main_pars["subtractbg"] == True):
                if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                    self.stack_all_images()
                else:
                    self.change_do_bg()

    def change_do_bg(self):
        """
        Called when the user changes the backgound option (yes/no)
        """

        if (self.do_bg_action.isChecked()):
            self.main_pars["subtractbg"] = True
            if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                self.stack_all_images()
            else:
                self.redraw_from_raw(self.sv.getFrameNumber())
        else:
            self.main_pars["subtractbg"] = False
            if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                self.stack_all_images()
            else:
                self.redraw_from_raw(self.sv.getFrameNumber())

    def changedatafiles(self):
        """
        Called when the user selects a menu to change the input data files

        Reads data and calls for a replot
        """

        filenames, _ = qt.QFileDialog.getOpenFileNames(
            None,
            "Select all EDF Files",
            None,
            "EDF Images (*.edf)")
        if filenames:
            # print("You selected %d images" % len(filenames))
            # Re-read the raw data
            rawdata = []
            self.omega = []
            for frame in filenames:
                im = fabio.open(frame)
                rawdata.append(im.data)
                if ("Omega" in im.header):
                    self.omega.append(float(im.header["Omega"]))
                else:
                    self.omega.append(numpy.nan)
            self.rawdata = numpy.asarray(rawdata)
            if (self.main_pars["stackimages"]): # Remove the stack option if it is set. We just read a new list of files
                self.main_pars["stackimages"] = False
                self.do_stack_action.setChecked(False)
            dlg =  qt.QMessageBox(self.sv)
            dlg.setWindowTitle("Data loaded...")
            dlg.setText("Data loaded from %d image(s)" % len(filenames))
            button = dlg.exec()
            self.redraw_from_raw(0)


    def changepeakfile(self):
        """
        Called when the user selects a menu to change the peak file
        """

        #print ("The user was to change the peak file")
        options = qt.QFileDialog.Options()
        fileName, _ = qt.QFileDialog.getOpenFileName(None, "Open a peak file", "", "FLT files (*.flt);;All files (*.*)", options=options)
        if fileName:
            self.readpeaks(fileName)

    def readpeaks(self,filename):
        """
        Function to read peaks from a file

        Send the file name
        """

        if (filename != None):
            #print("Reading peaks from %s" % main_pars["peakfile"])
            if (os.path.isfile(filename)):
                # Read peak informations from file
                try:
                    self.peaks["peakinfo"] = numpy.genfromtxt(filename, skip_header=1)
                    # Figure out important columns from header
                    infile = open(filename, 'r')
                    header = (infile.readline().strip('\n'))[1:].split()
                    infile.close()
                    self.peaks["dety"] = header.index("sc")
                    self.peaks["detz"] = header.index("fc")
                    self.peaks["Min_o"] = header.index("Min_o")
                    self.peaks["Max_o"] = header.index("Max_o")
                except (ValueError,LookupError) as e:
                    dlg =  qt.QMessageBox(self.sv)
                    dlg.setWindowTitle("Error loading file...")
                    dlg.setIcon(qt.QMessageBox.Critical)
                    dlg.setText("Error")
                    dlg.setInformativeText("Not a peak file or format error:\n%s" % os.path.split(filename)[1])
                    button = dlg.exec()
                    return False
                self.peaks["set"] = True
                self.main_pars["peakfile"] = filename
                self.qeditpeaks.setText(os.path.split(filename)[1])
                if (self.peaks["peakinfo"].shape[0] > 10000):
                    dlg =  qt.QMessageBox(self.sv)
                    dlg.setWindowTitle("Lots's of peaks")
                    dlg.setIcon(qt.QMessageBox.Warning)
                    dlg.setText("%d peaks: peak plotting peaks is disabled. Not recommended over 10000 peaks!" % self.peaks["peakinfo"].shape[0])
                    button = dlg.exec()
                    self.do_show_peaks_action.setChecked(False)
                    self.main_pars["show_peaks"] = False
                if (self.main_pars["show_peaks"]):
                    if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                        self.stack_all_images()
                    else:
                        # Force a replot
                        on_frame_changed(sv.getFrameNumber())
            else:
                dlg =  qt.QMessageBox(self.sv)
                dlg.setWindowTitle("Error loading file...")
                dlg.setIcon(qt.QMessageBox.Critical)
                dlg.setText("Error")
                dlg.setInformativeText("File not found : %s" % os.path.split(filename)[1])
                button = dlg.exec()
                return False
                # print("Error : file not found : %s" % main_pars["peakfile"])
        # print(header)
        # print(colsc,colfc,Min_o,Max_o)


    def changepeakcircleradius(self):
        """
        Called when the user selects a menu to change the peak circle radius
        """

        #print ("The user was to change the peak circle radius")
        roll, done = qt.QInputDialog.getInt(self.sv,'Peak circle radius', 'Peak cicle radius (in px):',value = self.main_pars["peakcircleradius"] )
        if (done):
            self.main_pars["peakcircleradius"] = roll
            # Force a replot
            if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                self.stack_all_images()
            else:
                self.on_frame_changed(self.sv.getFrameNumber())


    def change_show_peaks(self):
        """
        Called when the user selects a menu to show or not show peaks
        """

        if (self.do_show_peaks_action.isChecked()):
            self.main_pars["show_peaks"] = True
            # Force replot
            if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                self.stack_all_images()
            else:
                self.redraw_from_raw(self.sv.getFrameNumber())
            # print ("Show peaks")
        else:
            self.main_pars["show_peaks"] = False
            # print ("Do not show peaks")
            # Force replot
            if (self.main_pars["stackimages"]): # If the user wants a stack, special function to replot
                self.stack_all_images()
            else:
                self.redraw_from_raw(self.sv.getFrameNumber())


    def save_mean(self):
        """
        The user wants to save a mean image, let's go for it
        """

        datatmp = numpy.mean(self.rawdata, axis=0)
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

    def save_median(self):
        """
        The user wants to save a median image, let's go for it
        """

        datatmp = numpy.median(self.rawdata, axis=0)
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


    def stack_all_images(self):
        """
        Called when the user changes whether to stack all images or not

        Reads data and calls for a replot
        """

        if (self.do_stack_action.isChecked()): # The user wants a stack, we do it here
            self.main_pars["stackimages"] = True
            # take the mean of all frames
            datatmp = numpy.mean(self.rawdata, axis=0)
            # subtractbg if needed
            if (self.do_bg_action.isChecked() and (self.main_pars["bgfile"] != None)):
                bgim = fabio.open(self.main_pars["bgfile"])
                datatmp = datatmp-bgim.data
            # Apply flipping
            datatmp = image_flipping(datatmp,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])
            # Set data
            self.sv.setStack([datatmp])
            self.sv.setGraphTitle("Omega stack")
            # Add peaks here (omega filtering is different than for single frames)
            if (self.main_pars["show_peaks"] and self.peaks["set"]):
                # Extract the underlying PlotWidget
                plot_widget = self.sv.getPlotWidget()
                # Remove all "peaks" item
                plot_widget.remove(kind='curve')
                # Add relevant peaks
                omegamin = min(self.omega)
                omegamax = max(self.omega)
                # Need to apply the flip matrix to the peak position... Not sure on how to do that.
                # Brutal a stupid solution
                # Create an empy image, will set to 1 when there is a peak
                [dim0, dim1, dim2] = self.rawdata.shape
                peakpos = numpy.zeros([1,dim1,dim2],dtype=numpy.int8)
                npeaks = 0
                for peak in self.peaks["peakinfo"] :
                    if ((peak[self.peaks["Min_o"]] <= omegamax) and (omegamin <= peak[self.peaks["Max_o"]])):
                        cy = numpy.rint(peak[self.peaks["detz"]]).astype(int)
                        cx = numpy.rint(peak[self.peaks["dety"]]).astype(int)
                        # print(cx,cy)
                        peakpos[0,cx,cy] = 1
                        npeaks += 1
                if (npeaks > 1000):
                    dlg =  qt.QMessageBox(self.sv)
                    dlg.setWindowTitle("Lots's of peaks")
                    dlg.setIcon(qt.QMessageBox.Warning)
                    dlg.setText("%d peaks: plotting peaks is disabled over 1000 peaks in a stacked image. " % npeaks)
                    button = dlg.exec()
                    self.do_show_peaks_action.setChecked(False)
                    return
                # Apply image flipping to locate the peaks on flipped images
                peakpos = image_flipping(peakpos,self.main_pars["o11"],self.main_pars["o12"],self.main_pars["o21"],self.main_pars["o22"])
                # Search peaks and plot a circle
                drawpeaks = zip(*numpy.where(peakpos == 1))
                # print(drawpeaks)
                legendindex = 0
                for p,cx,cy in drawpeaks:
                    # print(p,cx,cy)
                    # print("Found one at %d %d" % (cx, cy))
                    # Define geometry
                    t = numpy.linspace(0, 2 * numpy.pi, 200)
                    x = cy + self.main_pars["peakcircleradius"] * numpy.cos(t)
                    y = cx + self.main_pars["peakcircleradius"] * numpy.sin(t)
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
                plot_widget = self.sv.getPlotWidget()
                plot_widget.remove(kind='curve')
        else: # The user does not want to stack images anymore, we redraw_from_raw
            self.main_pars["stackimages"] = False
            self.redraw_from_raw()



def main(argv):
    """
    Main subroutine
    """

    # Global variables with parameters, peaks from peak search info, rawdata, and omega values
    global main_pars,peaks,rawdata,omega
    # Gui elements: main window, on/off menu items to check at other places
    global sv, do_show_peaks_action, do_bg_action, do_stack_action, qeditbg, qeditpeaks

    qapp = qt.QApplication(sys.argv[1:])
    viewer = timelessViewer()
    qapp.exec_()

    return


# Calling method 1 (used when generating a binary in setup.py)
def run():
	main(sys.argv[1:])

# Calling method 2 (if run from the command line)
if __name__ == "__main__":
    main(sys.argv[1:])
