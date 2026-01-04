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

[[ -d logs ]] || mkdir -p logs

for FILE in original-files/*; do
  FILENAME=$(basename ${FILE})
  SHORTFILE="${FILENAME%.*}"
  TITLE=$(echo "${SHORTFILE}" | sed s'/_/ /g')
  # Clean up the file name to remove odd characters and newlines
  CLEAN_FILENAME=$(echo "${FILENAME}" | tr '\n\r' ' ' | tr -s ' ')

  ocrmypdf -q --title "${TITLE}" --output-type pdf "${FILE}" ocr-files/"${FILENAME}" &> logs/"${TITLE}".log 

  if [ $? -ne 0 ]; then
	echo "Trying "${FILE}" again with different parameters" &> logs/"${TITLE}".log
	 ocrmypdf -q --skip-text --title "${TITLE}" --output-type pdf "${FILE}" ocr-files/"${FILENAME}" &> logs/"${TITLE}".log 

  fi

  echo "Completed ${FILE}"

done
