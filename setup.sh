#!/usr/bin/env bash

uname -a | grep Darwin 2>&1 > /dev/null
if [ $? -ne 0 ]; then
  echo "This script is designed to run on macOS."
  echo "You can comment out this check if you want, but your mileage may vary"
  exit 1
fi

which brew 2>&1 > /dev/null
if [ $? -ne 0 ]; then
  echo "Please install homebrew from https://brew.sh"
  echo "This tool requires homebrew to be installed"
  exit 2
fi

which python 2>&1 > /dev/null
if [ $? -ne 0 ]; then
  echo "Installing python."
  brew -q install python@3.13
fi

python -m venv .venv && source .venv/bin/activate
if [ $? -ne 0 ]; then
  echo "Something went awry creating or activating the Python virtual environment."
  echo "You'll have to fix it yourself"
  exit 3
fi

pip install -r requirements.txt
if [ $? -eq 0 ]; then
  echo "Everything is all set. Put your PDFs in the 'original_files' folder"
  echo "Then run `./fmp-step1.sh`"
  exit 0
fi

exit 99
