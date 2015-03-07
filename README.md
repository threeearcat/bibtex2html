# Bibtex2html

This program reads a bibtex file and convert it to a list of references
in HTML format.

## Usage

To use this program you need a template file containing the following
placeholders:

    <!--NUMBER_OF_REFERENCES-->
    <!--NEWER-->
    <!--OLDER-->
    <!--DATE-->
    <!--LIST_OF_REFERENCES-->

These fields will be replaced by the program, and the result will be printed
out to the standard output.

To run type:

    python bibtex2html.py bibtex.bib template.html

or

    python bibtex2html.py bibtex.bib template.html > output.html

## License

Copyright (C) 2009-2015 Gustavo de Oliveira. Licensed under the GPL (see the
[license](LICENSE.txt) file).