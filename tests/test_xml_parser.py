import sys
import os
import pathlib
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import bigsdb.xml_parser as xml_parser

dir = pathlib.Path(__file__).parent.resolve()
xml_file = f'{dir}/config_files/config.xml'


class TestXmlParser(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestXmlParser, self).__init__(*args, **kwargs)
        self.parser = xml_parser.XML_Parser()
        self.parser.parse(xml_file)
               
    def test_system(self):
        system = self.parser.get_system()
        self.assertEqual(system['db'], 'pubmlst_bigsdb_neisseria_isolates')
        
    def test_field_list(self):
        fields = self.parser.get_field_list()
        self.assertEqual(len(fields), 71)
        self.assertIn('country', fields)
        
    def test_all_field_attributes(self):
        attributes = self.parser.get_all_field_attributes()
        self.assertEqual(attributes['year']['required'], 'expected')
        
    def test_field_attributes(self):
        attributes = self.parser.get_field_attributes('year')
        self.assertEqual(attributes['required'], 'expected')
        
    def test_field_option_list(self):
        options = self.parser.get_field_option_list('source')
        self.assertEqual(len(options), 10)
        self.assertEqual(options[2], 'eye')
    
        
if __name__ == '__main__':
    unittest.main()
