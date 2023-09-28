PyMovie
=======

PyMovie is a simple (hopefully) application for extracting lightcurves from occultation videos.

It is specially designed to be robust in both star tracking and data extraction when the
video has been disturbed by wind-shake.

The name was chosen out of respect and deference to LiMovie, a pioneer application
published many years ago.
This application has fewer 'bells and whistles' than LiMovie and so should be easier
to use for a newbie.


Astrid RAVF support
====================

This repository is forked from Bob Andersons pymovie repository.

Prior to integration into the main distribution, to install pymovie with RAVF support replace:

	pip install pymovie


in the installation instructions with:

	pip install --upgrade pip
	
	pip install ravf
	
	pip install "git+https://github.com/ChasinSpin/pymovie.git"


To upgrade an existing installation of pymovie:

	pip install --upgrade pip
	
	pip install --upgrade ravf
	
	pip install --upgrade --force-reinstall "git+https://github.com/ChasinSpin/pymovie.git"



Further information on the RAVF format and the ravf package can be found here:
	http://www.github.com/ChasinSpin/ravf
