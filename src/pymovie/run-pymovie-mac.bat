#!/bin/bash

cd ~/Anaconda3

# Create/overwrite python script for starting up PyMovie
echo "from pymovie import main" >  run-pymovie.py
echo "main.main()"              >> run-pymovie.py

# Activate the Anaconda3 (base) environment
source activate

# Use python to execute the startup script created above
python run-pymovie.py

# If you're having trouble with this script and need to see more info,
# uncomment the following lines to keep the script from closing
#echo "Press enter to exit: "
#read anything