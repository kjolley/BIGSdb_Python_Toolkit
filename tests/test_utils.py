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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not, 
# see <http://www.gnu.org/licenses/>.

import sys
import os
import pathlib
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import bigsdb.utils as utils

class TestUtils(unittest.TestCase):
    
    def test_is_integer(self):
        self.assertTrue(utils.is_integer('345'))
        self.assertTrue(utils.is_integer('-12'))
        self.assertFalse(utils.is_integer('abc'))
        self.assertFalse(utils.is_integer('5.6'))
        self.assertFalse(utils.is_integer('2024-01-01'))
    
    def test_is_float(self):
        self.assertTrue(utils.is_float('345'))
        self.assertTrue(utils.is_float('5.6'))
        self.assertTrue(utils.is_float('-12.3'))
        self.assertFalse(utils.is_float('2024-01-01'))
        
    def test_is_date(self):
        self.assertTrue(utils.is_date('2024-01-01'))
        self.assertFalse(utils.is_date('2024-02-30'))
        self.assertFalse(utils.is_date('5/6/2023'))
        self.assertFalse(utils.is_date('345'))
        self.assertFalse(utils.is_date('-12'))
        self.assertFalse(utils.is_date('-12.3'))
        
        