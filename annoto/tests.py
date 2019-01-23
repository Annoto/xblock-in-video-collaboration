import mock
import json
import unittest
from ddt import ddt

from xblock.field_data import DictFieldData

from .annoto import AnnotoXBlock


@ddt
class AnnotoXBlockTests(unittest.TestCase):
    def make_one(self, **kw):
        """
        Creates a AnnotoXBlock for testing purpose.
        """
        field_data = DictFieldData(kw)
        block = AnnotoXBlock(mock.Mock(), field_data, mock.Mock())
        block.location = mock.Mock(
            block_id='block_id',
            org='org',
            course='course',
            block_type='block_type'
        )
        return block

    def test_default_filelds_values(self):
        block = self.make_one()
        self.assertEqual(block.display_name, 'Annoto')
        self.assertEqual(block.widget_position, 'top-right')
        self.assertTrue(block.tabs)
        self.assertTrue(block.discussions_scope)

    def test_set_fields_custom_values(self):
        block = self.make_one()

        fields = {
            'display_name': 'Test Annoto',
            'widget_position': 'bottom-left',
            'tabs': False,
            'discussions_scope': False
        }

        block.submit_studio_edits(mock.Mock(method="POST",
            body=json.dumps({'values': fields, 'defaults': [block.editable_fields]})))

        self.assertEqual(block.display_name, 'Test Annoto')
        self.assertEqual(block.widget_position, 'bottom-left')
        self.assertFalse(block.tabs)
        self.assertFalse(block.discussions_scope)

    def test_position_parser(self):
        block = self.make_one()
        self.assertEqual(block.get_position(), (u'right', u'top'))
