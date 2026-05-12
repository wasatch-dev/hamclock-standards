#!/bin/bash

############################3
# See README.md
############################3

if ! pandoc -v 2>&1 >/dev/null; then
    echo "Please install the pandoc package."
    exit 1
fi

# generate the plain text table [api-doc.txt](api-doc.txt).
echo "Generating the plain text table ..."
python3 md-to-doc.py api-doc.md > api-doc.txt

# generate the OpenAPI specification [hamclock-openapi.yaml](hamclock-openapi.yaml).
echo "Generating the OpenAPI specification ..."
python3 md-to-openapi.py api-doc.md hamclock-openapi.yaml

# generate the interactive HTML documentation [hamclock-api-docs.html](hamclock-api-docs.html).
echo "Generating the interactive OpenAPI HTML documentation ..."
python3 openapi-to-html.py

# convert MarkDown (MD) to HTML
echo "Converting MarkDown to HTML ..."
pandoc api-doc.md -so api-doc.html

