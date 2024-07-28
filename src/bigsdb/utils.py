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

from datetime import datetime


def get_datestamp():
	return datetime.today().strftime('%Y-%m-%d')


def get_current_year():
	return datetime.today().strftime('%Y')


def is_integer(n):
    try:
        int(n)
        return True
    except ValueError:
        return False

       
def is_float(n):
    try:
        float(n)
        return True
    except ValueError:
        return False


def is_date(string, format="%Y-%m-%d"):
    try:
        datetime.strptime(string, format)
        return True
    except ValueError:
        return False

    
def escape_html(string):
	if string == None:
		return
	string = string.replace('&', '&amp;')
	string = string.replace('"', '&quot;')
	string = string.replace('<', '&lt;')
	string = string.replace('>', '&gt;')
	return string
	
