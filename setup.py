#!/usr/bin/env python


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

#from distutils.core import setup,Extension
from setuptools import setup,Extension
import sys

from distutils import util

if sys.version_info < (3,0):
    sys.exit('Sorry, Python 2 is not supported. This should be run in python3 or later')
    
setup(
	name='TIMEleSS_Viewer',
	python_requires='>3.0.0',
	version='0.0.5',
	description='Diffraction data explorer for the Multigrain Crystallography toolbox from the TIMEleSS project',
	license='GPL', 
	maintainer='Sebastien Merkel',
	maintainer_email='sebastien.merkel@univ-lille.fr',
	url = 'https://github.com/FABLE-3DXRD/TIMEleSS_Viewer',
	project_urls={
    'Documentation': 'http://multigrain.texture.rocks/',
    'Source': 'https://github.com/FABLE-3DXRD/TIMEleSS_Viewer',
    'Science project': 'http://timeless.texure.rocks',
	},
	
	install_requires=['fabio','PyQt5', 'silx', 'numpy'],
	
	package_dir = {
				'TIMEleSS_Viewer': 'TIMEleSS_Viewer'},
	packages=['TIMEleSS_Viewer'],
	
	
	entry_points = {
		'gui_scripts': [
		    'timelessViewer = TIMEleSS_Viewer.timelessViewer:run'
		]
	}
)
