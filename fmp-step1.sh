#!/usr/bin/env bash

echo "This script will look at all of the files in 'original-files"
echo "If they need OCR text added, it will add it"
echo "If they need a title metadata element, it will add it, based on the name of the file"
echo "Your original files will not be changed"
echo ""
echo "If you want to not do this, enter quit below"
echo "Otherwise press enter to get the process started"
read QUIT

[[ ${QUIT} == 'quit' ]] && exit 1

for FILE in original-files/*; do
  FILENAME=$(basename ${FILE})
  SHORTFILE="${FILENAME%.*}"
  TITLE=$(echo "${SHORTFILE}" | sed s'/_/ /g')
  # Clean up the file name to remove odd characters and newlines
  CLEAN_FILENAME=$(echo "${FILENAME}" | tr '\n\r' ' ' | tr -s ' ')

  ocrmypdf -q --title "${TITLE}" --output-type pdfa "${FILE}" ocr-files/"${FILENAME}" &> /dev/null

  # Exit code 6 means that text is already there, I think
  [ $? -eq 6 ] && ocrmypdf -q --skip-text --title "${TITLE}" --output-type pdfa "${FILE}" ocr-files/"${FILENAME}" &> /dev/null

  echo "Completed ${FILE}"

done