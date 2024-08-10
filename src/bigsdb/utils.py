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
from datetime import datetime


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
