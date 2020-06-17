import jwt
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
        self.assertEqual(block.widget_position, 'top-left')
        self.assertTrue(block.overlay_video)
        self.assertEqual(block.tabs, 'enabled')
        self.assertEqual(block.initial_state, 'auto')
        self.assertTrue(block.discussions_scope)

    def test_set_fields_custom_values(self):
        block = self.make_one()

        fields = {
            'display_name': 'Test Annoto',
            'widget_position': 'bottom-left',
            'overlay_video': False,
            'tabs': 'hidden',
            'initial_state': 'open',
            'discussions_scope': False
        }

        block.submit_studio_edits(mock.Mock(method="POST",
            body=json.dumps({'values': fields, 'defaults': [block.editable_fields]})))

        self.assertEqual(block.display_name, 'Test Annoto')
        self.assertEqual(block.widget_position, 'bottom-left')
        self.assertFalse(block.overlay_video)
        self.assertEqual(block.tabs, 'hidden')
        self.assertEqual(block.initial_state, 'open')
        self.assertFalse(block.discussions_scope)

    def test_position_parser(self):
        block = self.make_one()
        self.assertEqual(block.get_position(), (u'right', u'top'))

    @mock.patch('annoto.AnnotoXBlock.get_course_obj')
    def test_get_annoto_settings(self, get_course_obj_mock):
        except_auth = {
            'name': 'annoto-auth',
            'client_id': 'test_id',
            'client_secret': 'test_secret'
        }
        lti_passports = [
            'another_passport:another_client_id:another_client_secret',
            '{name}:{client_id}:{client_secret}'.format(**except_auth)
        ]

        block = self.make_one()
        get_course_obj_mock.return_value = mock.Mock(lti_passports=lti_passports)

        self.assertDictEqual(block.get_annoto_settings(), except_auth)

    @mock.patch('annoto.annoto.time')
    @mock.patch('annoto.AnnotoXBlock.get_course_obj')
    @mock.patch('annoto.AnnotoXBlock._build_absolute_uri')
    @mock.patch('annoto.annoto.get_profile_image_urls_for_user')
    def test_get_jwt_token(self, get_profile_image_urls_for_user_mock,
                           build_absolute_uri_mock, get_course_obj_mock, time_mock):
        client_id = 'test_id'
        lti_passports = ['annoto-auth:{}:test_secret'.format(client_id)]

        expect_payload = {
            u'expire': 1234567,
            u'iss': u'test_id',
            u'jti': u'test_user_id',
            u'name': u'test_user_name',
            u'email': u'test_user_email',
            u'photoUrl': u'test_user_photo_url'
        }

        profile_mock = mock.Mock()
        profile_mock.configure_mock(name=expect_payload['name'])

        user_mock = mock.Mock(
            email=expect_payload['email'],
            profile=profile_mock
        )
        user_mock.configure_mock(id=expect_payload['jti'])

        block = self.make_one()

        block.runtime = mock.Mock(service=mock.Mock(return_value=mock.Mock(_django_user=user_mock)))
        get_course_obj_mock.return_value = mock.Mock(lti_passports=lti_passports)
        get_profile_image_urls_for_user_mock.return_value = {'small': 'empty'}
        build_absolute_uri_mock.return_value = expect_payload['photoUrl']
        time_mock.configure_mock(time=mock.Mock(return_value=expect_payload['expire'] - 60 * 20))

        auth = block.get_annoto_settings()

        resp = block.get_jwt_token(self, None).json
        self.assertEqual(resp['status'], 'ok')

        actual_payload = jwt.decode(resp['token'], auth['client_secret'], algorithms=['HS256'])
        self.assertDictEqual(actual_payload, expect_payload)
