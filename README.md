# Batch fix some pdfs for a headstart with Section 508 compliance.

## Disclaimer
The output from this WILL NOT create PDFs that 100% 508 compliant. This is simply designed to help take some of the more menial tasks out of the way.

## Requirements
  * homebrew (if you are on a Mac)
  * python3.10 or higher
  * ocrmypdf (installed via homebrew)

## Usage
I'm trying to make this as simple as possible. 

If you are on a Mac, you can use `setup.sh` to get everything ready. Open a terminal and run `sh fmp-step1.sh`
If that completes successfully, then you will have PDFs in the `ocr-files` directory that are fully ready for OCR and have a title metadata value set.

The last step is to run `python3 fmp-step2.py`. If that completes successfully, then there'll be PDFs in the `tagged-files` folder that will have some very basic tagging in place.

