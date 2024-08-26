# Written by Keith Jolley
# Copyright (c) 2024, University of Oxford
# E-mail: keith.jolley@biology.ox.ac.uk
#
# This file is part of BIGSdb Python Toolkit.
#
# BIGSdb Python Toolkit is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BIGSdb Python Toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not,
# see <https://www.gnu.org/licenses/>.

import os
import random
import hashlib
import xlsxwriter
import re
from datetime import datetime
from itertools import islice
from collections import defaultdict
from typing import List, Dict


def get_datestamp():
    return datetime.today().strftime("%Y-%m-%d")


def get_current_year():
    return datetime.today().strftime("%Y")


def is_integer(n):
    if n == None:
        return False
    try:
        int(n)
        return True
    except ValueError:
        return False


def is_float(n):
    if n == None:
        return False
    try:
        float(n)
        return True
    except ValueError:
        return False


def is_date(string, format="%Y-%m-%d"):
    if string == None:
        return False
    try:
        datetime.strptime(string, format)
        return True
    except ValueError:
        return False


def escape_html(string):
    if string == None:
        return
    string = string.replace("&", "&amp;")
    string = string.replace('"', "&quot;")
    string = string.replace("<", "&lt;")
    string = string.replace(">", "&gt;")
    return string


def get_random():
    return (
        "BIGSdb_"
        + "{}".format(os.getpid())
        + "_"
        + "{:010d}".format(random.randint(0, 9999999999))
        + "_"
        + "{:05d}".format(random.randint(0, 99999))
    )


def create_string_from_list(int_list, separator="_"):
    str_list = [str(i) for i in int_list]
    return separator.join(str_list)


def get_md5_hash(input_string):
    hasher = hashlib.md5()
    hasher.update(input_string.encode("utf-8"))
    return hasher.hexdigest()


# Splits an iterable into batches of size n.
def batch(iterable, n=1):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk


def text2excel(text_file, options={}):
    text_fields = {}
    text_cols = {}

    if "text_fields" in options:
        text_fields = {field: 1 for field in options["text_fields"].split(",")}

    # Always use text format for likely record names
    for field in ["isolate", "strain", "sample"]:
        text_fields[field] = 1

    if "stdout" in options and options["stdout"]:
        excel_file = None
    else:
        excel_file = text_file.replace("txt", "xlsx")

    workbook = xlsxwriter.Workbook(excel_file)
    text_format = workbook.add_format({"num_format": "@", "align": "center"})
    workbook.use_zip64()

    worksheet_name = options.get("worksheet", "output")
    worksheet = workbook.add_worksheet(worksheet_name)
    header_format = workbook.add_format({"align": "center", "bold": True})
    cell_format = workbook.add_format({"align": "center"})

    with open(text_file, "r", encoding="utf-8") as text_fh:
        row = 0
        col = 0
        widths = {}
        first_line = True
        special_values = {"="}
        max_col = 1

        for line in text_fh:
            line = line.rstrip("\n").replace("\r", "").replace("\n", " ")
            format = (
                header_format
                if not options.get("no_header", False) and row == 0
                else cell_format
            )
            values = line.split("\t")

            for value in values:
                if (
                    not options.get("no_header", False)
                    and first_line
                    and value in text_fields
                ):
                    text_cols[col] = 1

                if not first_line and col in text_cols:
                    worksheet.write_string(row, col, value, text_format)
                else:
                    if value in special_values:
                        worksheet.write_string(row, col, value, format)
                    else:
                        worksheet.write(row, col, value, format)

                widths[col] = max(widths.get(col, 0), len(value))
                max_col = max(max_col, col)
                col += 1

            col = 0
            row += 1
            first_line = False

        for col, width in widths.items():
            width = int(0.9 * width + 2)
            if "max_width" in options:
                width = min(width, options["max_width"])
            worksheet.set_column(col, col, width)

        if not options.get("no_header", False):
            worksheet.freeze_panes(1, 0)

        if "conditional_formatting" in options:
            for formatting in options["conditional_formatting"]:
                format = workbook.add_format(formatting["format"])
                col_letter = xlsxwriter.utility.xl_col_to_name(formatting["col"])
                if formatting.get("apply_to_row", False):
                    worksheet.conditional_format(
                        1,
                        0,
                        row - 1,
                        max_col,
                        {
                            "type": "formula",
                            "criteria": f'=${col_letter}2="{formatting["value"]}"',
                            "format": format,
                        },
                    )
                else:
                    worksheet.conditional_format(
                        1,
                        formatting["col"],
                        row - 1,
                        formatting["col"],
                        {
                            "type": "cell",
                            "criteria": "==",
                            "value": f'"{formatting["value"]}"',
                            "format": format,
                        },
                    )

    workbook.close()
    return excel_file


def convert_to_defaultdict(d):
    if isinstance(d, dict):
        return defaultdict(dict, {k: convert_to_defaultdict(v) for k, v in d.items()})
    return d


def dictionary_sort(values: List[str], labels: Dict[str, str]) -> List[str]:
    def normalize(label: str) -> str:
        return re.sub(r"[\W_]+", "", label.lower())

    unique_values = list(set(values))
    sorted_values = sorted(unique_values, key=lambda x: normalize(labels[x]))
    return sorted_values
