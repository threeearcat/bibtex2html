#! /usr/bin/env python3


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
import re
import os
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
        "\\'\\": "",
        "{": "",
        "}": "",
        " And ": " and ",
    }

    for k, v in dictionary.items():
        s = s.replace(k, v)

    s = s.strip()

    authors = s.split("and")
    s = ""
    for author in authors:
        if s != "":
            s += ", "
        before, sep, after = author.partition(",")
        s += after.strip() + " " + before.strip()

    if len(authors) > 1:
        before, sep, after = s.rpartition(",")
        s = before + ", and " + after
        s = re.sub(r"\s+", " ", s)
    return s


def cleanup_title(s):
    """Clean up and format article titles.

    cleanup_title(str) -> str
    """

    s = re.sub(r"[^a-zA-Z\s\n\.0-9\(\):\-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+:", ":", s)

    # TODO: clean up titles
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

    listlist.reverse()

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

    def canonicalize_booktitle(title, strdict):
        for k in strdict:
            v = strdict[k]
            if k.upper() == title:
                title = v
                break
        title = re.sub(r"[^a-zA-Z\s\n\.0-9\(\)&]", " ", title)
        title = re.sub(r"\s+", " ", title)
        return title

    crossref = {}
    for d in dictlist:
        if "type" not in d:
            continue
        if d["type"] == "proceedings":
            key = d["id"]
            d["booktitle"] = canonicalize_booktitle(d["title"], strdict)
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

    cls = os.path.basename(bibfile).removesuffix(".bib")

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
        dlower["class"] = cls
        if "journal" in dlower and "booktitle" not in dlower:
            dlower["booktitle"] = dlower["journal"]
        dictlist.append(dlower)

    # Keep only articles in the list
    dictlist = [d for d in dictlist if d["type"] in ["inproceedings", "article"]]
    # keep only articles that have author and title
    dictlist = [d for d in dictlist if "author" in d and "title" in d]
    dictlist = [d for d in dictlist if d["author"] != "" and d["title"] != ""]

    # Clean up data
    for i in range(len(dictlist)):
        dictlist[i]["author"] = cleanup_author(dictlist[i]["author"])
        dictlist[i]["title"] = cleanup_title(dictlist[i]["title"])

    return dictlist

def bold_me(dictlist):
    bolded_me = "<u>" + me + "</u>"
    for d in dictlist:
        d['author'] = d['author'].replace(me, bolded_me)


def monthToNum(d):
    if 'month' not in d:
        return 0
    m = d['month']
    try:
        return int(m)
    except:
        months =  {
            'jan': 1,
            'feb': 2,
            'mar': 3,
            'apr': 4,
            'may': 5,
            'jun': 6,
            'jul': 7,
            'aug': 8,
            'sep': 9,
            'oct': 10,
            'nov': 11,
            'dec': 12,
        }
        return months[m]

def get_result(dictlist, cls, format_entry):
    # Get a list of the article years and the min and max values
    years = [int(d["year"]) for d in dictlist if "year" in d]
    years.sort()
    older = years[0]
    newer = years[-1]

    result = ""
    print_header = True
    for y in reversed(range(older, newer + 1)):
        if y in years:
            global print_year
            if print_year:
                result += "# {}\\\n".format(y)
                print_header = True
            if print_header and print_table:
                result += "|<-->|<-->|\n"
                result += "|-|----------------------------|\n"
                print_header = False

            printing = []
            for d in dictlist:
                if cls != "all" and ("class" not in d or d["class"] != cls):
                    continue

                if "year" in d and int(d["year"]) == y:
                    printing.append(d)

            # printing.sort(key=lambda d: monthToNum(d), reverse=True)
            for d in printing:
                result += format_entry(d)
    return result

def print_result(dictlist, template, format_entry):

    bold_me(dictlist)

    # Write down the list html code
    all = get_result(dictlist, "", format_entry)
    intl = get_result(dictlist, "intl", format_entry)
    misc = get_result(dictlist, "misc", format_entry)

    # Fill up the empty fields in the template
    template = template.replace("<!--LIST_OF_REFERENCES-->", all)
    template = template.replace("<!--LIST_OF_INTL-->", intl)
    template = template.replace("<!--LIST_OF_MISC-->", misc)
    template = template.replace("<!--DATE-->", date.today().strftime("%d %b %Y"))
    for d in dictlist:
        template = template.replace("<!--{}-->".format(d["id"]), format_entry(d))

    # Write the final result
    final = template
    print(final)


# Set the fields to be exported to html (following this order)
mandatory = ["title", "year", "author", "booktitle"]
optional = ["paper", "slide", "code"]
classes = {
    "paper": "paper",
    "slide": "slide",
    "code": "code",
}

def styling(s):
    return "<span class=\"{}\">{}</span>".format(classes[s], s)

def format_optional(d):
    global skip_optional
    if skip_optional:
        return ""
    optdata = ""
    for opt in optional:
        if opt not in d:
            continue
        optdata += "[[**{}**]({})]".format(styling(opt), d[opt])
    return optdata

def format_misc(d):
    global skip_optional
    if skip_optional:
        return ""
    return "" if "misc" not in d else "\\\n<span class=\"misc\">"+d["misc"]+"</span>"

def format_comment(d):
    global skip_optional
    if skip_optional:
        return ""
    return "" if "comment" not in d else "\\\n<span class=\"comment\">"+d["comment"]+"</span>"

def format_abbrv(d):
    if "abbrv" in d:
        return "**{}**".format(d["abbrv"])
    else:
        return ""

def __get_data(d):
    d["booktitle"] = re.sub(r'\(([A-Za-z&]*)\)', r'(**\1**)', d["booktitle"])
    optdata = format_optional(d)
    miscdata = format_misc(d)
    commentdata = format_comment(d)
    prefix = "({}) ".format(d["prefix"]) if "prefix" in d else ""
    abbrv = format_abbrv(d)
    data = [d[key] for key in mandatory]
    data.append(optdata)
    data.append(miscdata)
    data.append(commentdata)
    data.append(prefix)
    data.append(abbrv)
    return data


def format_entry_markdown_table(d):
    data = __get_data(d)
    markdown = "|{8}|**{7}{0} {4}**\\\n{2}\\\n{3}, {1}{5}{6}|\n".format(*data)
    return markdown


def format_entry_markdown_list(d):
    data = __get_data(d)
    markdown = "- **{6}{0} {4}**\\\n{2}\\\n{3}, {1}{5}\n".format(*data)
    return markdown


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

    if print_table:
        format_entry_markdown = format_entry_markdown_table
    else:
        format_entry_markdown = format_entry_markdown_list
    print_result(dictlist, template, format_entry_markdown)


print_year = False
me = "Dae R. Jeong"
skip_optional = True if "SKIP_OPTIONAL" in os.environ else False
print_table = True if "PRINT_TABLE" in os.environ else False
main()
