#! /usr/bin/env python


"""
Copyright (C) 2009-2021 Gustavo de Oliveira.
Licensed under the GNU GPLv2 (see License).

https://github.com/goliveira/bibtex2html


Bibtex2html reads a BibTeX file and converts it to a list of
references in HTML format.

## File description

* `bibtex2html.py`: the bibtex2html program
* `example.bib`: example of BibTeX file
* `template.html`: example of template file

## Usage

To run the program, execute the following command in a terminal:

    python bibtex2html.py example.bib template.html output.html

Here, `bibtex.bib` is the BibTeX file that you want to convert, and
`template.html` is any template file containing the following
placeholders:

    <!--NUMBER_OF_REFERENCES-->
    <!--NEWER-->
    <!--OLDER-->
    <!--DATE-->
    <!--LIST_OF_REFERENCES-->

These placeholders will be replaced by the program, and the result
will be written to the file `output.html`.

Alternatively, the command

    python bibtex2html.py example.bib template.html

prints the result to the standard output.
"""


import sys
import copy
from datetime import date


def cleanup_author(s):
    """Clean up and format author names.

    cleanup_author(str) -> str
    """

    dictionary = {
        '\\"a': "&auml;",
        '\\"A': "&Auml;",
        '\\"e': "&euml;",
        '\\"E': "&Euml;",
        '\\"i': "&iuml;",
        '\\"I': "&Iuml;",
        '\\"o': "&ouml;",
        '\\"O': "&Ouml;",
        '\\"u': "&uuml;",
        '\\"U': "&Uuml;",
        "\\'a": "&aacute;",
        "\\'A": "&Aacute;",
        "\\'e": "&eacute;",
        "\\'i": "&iacute;",
        "\\'I": "&Iacute;",
        "\\'E": "&Eacute;",
        "\\'o": "&oacute;",
        "\\'O": "&Oacute;",
        "\\'u": "&uacute;",
        "\\'U": "&Uacute;",
        "\\~n": "&ntilde;",
        "\\~N": "&Ntilde;",
        "\\~a": "&atilde;",
        "\\~A": "&Atilde;",
        "\\~o": "&otilde;",
        "\\~O": "&Otilde;",
        ".": " ",
        "\\'\\": "",
        "{": "",
        "}": "",
        " And ": " and ",
    }

    for k, v in dictionary.items():
        s = s.replace(k, v)

    s = s.strip()

    before, sep, after = s.rpartition(" and ")
    before = before.replace(" and ", ", ")
    s = before + sep + after

    return s


def cleanup_title(s):
    """Clean up and format article titles.

    cleanup_title(str) -> str
    """

    s = s.lower()
    s = s.capitalize()

    return s


def cleanup_page(s):
    """Clean up the article page string.

    cleanup_pages(str) -> str
    """

    s = s.replace("--", "-")

    return s


def extract_bibitem(datalist):
    # Discard unwanted characteres and commented lines
    datalist = [s.strip(" \n\t") for s in datalist]
    datalist = [s for s in datalist if s[:2] != "%%"]

    # Convert a list into a string
    data = ""
    for s in datalist:
        data += s + "\n"

    # Split the data at the separators @ and put it in a list
    biblist = data.split("@")
    # Discard empty strings from the list
    biblist = [s for s in biblist if s != ""]

    # Create a list of lists containing the strings "key = value" of each bibitem
    listlist = []
    for s in biblist:
        type, sep, s = s.partition("{")
        id, sep, s = s.partition(",")
        s = s.rpartition("}")[0]
        keylist = ["type = " + type.lower(), "id = " + id]

        # Uncomment for debugging
        # print(keylist)
        # print(s)

        number = 0
        flag = 0
        i = 0
        separator = "empty"

        for k in s.split("\n"):
            if len(k) != 0:
                keylist.append(k)

        keylist = [t.strip(" ,\t\n") for t in keylist]
        listlist.append(keylist)

    # Create a list of dicts containing key : value of each bibitem
    dictlist = []
    for l in listlist:
        keydict = {}
        for s in l:
            key, sep, value = s.partition("=")
            key = key.strip(" ,\n\t{}")
            key = key.lower()
            value = value.strip(' ,\n\t{}"')
            keydict[key] = value

        dictlist.append(keydict)

    return dictlist


def extract_crossref(bibfile):
    with open(bibfile, "r") as f:
        datalist = f.readlines()

    dictlist = extract_bibitem(datalist)

    strdict = {}
    for d in dictlist:
        if "type" not in d:
            continue
        if d["type"] == "string":
            s = d["id"]
            key, sep, value = s.partition("=")
            key = key.strip(" ,\n\t{}")
            key = key.lower()
            value = value.strip(' ,\n\t{}"')
            strdict[key] = value

    def canonicalize_title(title, strdict):
        import re

        for k in strdict:
            v = strdict[k]
            title = title.replace(k.upper(), v)
        title = re.sub(r"[^a-zA-Z\s\n\.0-9\(\)]", " ", title)
        title = re.sub(r"\s+", " ", title)
        return title

    crossref = {}
    for d in dictlist:
        if "type" not in d:
            continue
        if d["type"] == "proceedings":
            key = d["id"]
            d["crossref_title"] = canonicalize_title(d["title"], strdict)
            del d["title"]
            del d["type"]
            del d["id"]
            crossref[key] = d

    return crossref


def replace_crossref(value, key, crossref):
    return value if key != "crossref" or value not in crossref else crossref[value]


def translate_bibtex_to_dictionary(bibfile, crossref):
    with open(bibfile, "r") as f:
        datalist = f.readlines()

    dictlist = extract_bibitem(datalist)

    # Backup all the original data
    dictlist_bkp = copy.deepcopy(dictlist)

    # Lower case of all keys in dictionaries
    dictlist = []
    for d in dictlist_bkp:
        dlower = {k: v for (k, v) in d.items()}
        if "crossref" in dlower:
            k = dlower["crossref"]
            if k in crossref:
                dlower = dlower | crossref[k]
        dictlist.append(dlower)

    # Keep only articles in the list
    dictlist = [d for d in dictlist if d["type"] == "inproceedings"]
    # keep only articles that have author and title
    dictlist = [d for d in dictlist if "author" in d and "title" in d]
    dictlist = [d for d in dictlist if d["author"] != "" and d["title"] != ""]

    # Clean up data
    for i in range(len(dictlist)):
        dictlist[i]["author"] = cleanup_author(dictlist[i]["author"])
        dictlist[i]["title"] = cleanup_title(dictlist[i]["title"])

    return dictlist


def print_html(dictlist, template):
    # Get a list of the article years and the min and max values
    years = [int(d["year"]) for d in dictlist if "year" in d]
    years.sort()
    older = years[0]
    newer = years[-1]

    # Set the fields to be exported to html (following this order)
    mandatory = ["title", "year", "author"]
    optional = ["crossref_title", "url"]

    # Write down the list html code
    counter = 0
    html = ""
    for y in reversed(range(older, newer + 1)):
        if y in years:
            html += '<h3 id="y{0}">{0}</h3>\n\n\n<ul>\n'.format(y)
            for d in dictlist:
                if "year" in d and int(d["year"]) == y:
                    mandata = [d[key] for key in mandatory]
                    html += "<li><strong>{0}, {1}<strong>\n{2}".format(*mandata)

                    for t in optional:
                        if t in d:
                            if t == "crossref_title":
                                html += "\n{0}".format(d[t])
                            # if t == "url":
                            #     html += ' <a href="{0}">[html]</a>'.format(d[t])

                    html += "</li>\n"
                    counter += 1

            html += "</ul>\n"

    print(dictlist)

    # Fill up the empty fields in the template
    Template = template.replace("<!--LIST_OF_REFERENCES-->", html)
    tempalte = template.replace("<!--DATE-->", date.today().strftime("%d %b %Y"))

    # Join the header, list and footer html code
    final = template

    # Write the final result to the output file or to stdout
    print(final)


def main():
    # Get the BibTeX, template, and output file names
    if len(sys.argv) < 3:
        sys.exit("Error: Invalid command.")

    bibfiles = sys.argv[1].split(",")
    templatefile = sys.argv[2]

    # Open, read and close the BibTeX and template files
    with open(templatefile, "r") as f:
        template = f.read()

    crossref = {}
    for bibfile in bibfiles:
        crossref = crossref | extract_crossref(bibfile)

    # print("crossref: ", crossref)

    dictlist = []
    for bibfile in bibfiles:
        dictlist.extend(translate_bibtex_to_dictionary(bibfile, crossref))

    # print("dictlist: ", dictlist)

    print_html(dictlist, template)


main()
