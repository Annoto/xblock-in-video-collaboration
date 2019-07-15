import jwt
import time
import json
import logging
from webob import Response
from django.conf import settings
from django.http.request import HttpRequest
from django.template import Context, Template

import pkg_resources
from xblock.core import XBlock
from xblock.fields import Scope, String, Boolean
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.lib.courses import course_image_url
from student.roles import CourseInstructorRole, CourseStaffRole, GlobalStaff

from .fields import NamedBoolean

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

log = logging.getLogger(__name__)


@XBlock.needs('i18n', 'user')
class AnnotoXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Annoto",
        scope=Scope.settings,
    )
    widget_position = String(
        display_name=_("Widget Position"),
        values=(
            {'display_name': _('top-left'), 'value': 'top-left'},
            {'display_name': _('top-right'), 'value': 'top-right'},
            {'display_name': _('left'), 'value': 'left'},
            {'display_name': _('right'), 'value': 'right'},
            {'display_name': _('bottom-left'), 'value': 'bottom-left'},
            {'display_name': _('bottom-right'), 'value': 'bottom-right'}
        ),
        default="top-left",
    )

    overlay_video = Boolean(
        display_name=_("Overlay Video"),
        default=True
    )

    tabs = String(
        display_name=_("Tabs"),
        values=(
            {'display_name': _('Auto'), 'value': 'auto'},
            {'display_name': _('Enabled'), 'value': 'enabled'},
            {'display_name': _('Hidden'), 'value': 'hidden'}
        ),
        default="auto",
    )

    initial_state = String(
        display_name=_("Initial State"),
        values=(
            {'display_name': _('Auto'), 'value': 'auto'},
            {'display_name': _('Open'), 'value': 'open'},
            {'display_name': _('Closed'), 'value': 'closed'}
        ),
        default="auto",
    )

    discussions_scope = NamedBoolean(
        display_name=_('Discussions Scope'),
        display_true=_('Private per course'),
        display_false=_('Site Wide'),
        default=True
    )

    editable_fields = ('display_name', 'widget_position', 'overlay_video', 'tabs', 'initial_state' , 'discussions_scope')

    has_author_view = True

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_position(self):
        """Parse 'widget_position' field"""
        pos_list = self.widget_position.split('-')
        horisontal = len(pos_list) > 1 and pos_list[1] or pos_list[0]
        vertical = len(pos_list) > 1 and pos_list[0] or 'center'
        return (horisontal, vertical)


    def author_view(self, context=None):
        context = context or {}
        context['is_author_view'] = True
        return self._base_view(context=context)

    def student_view(self, context=None):
        """
        The primary view of the AnnotoXBlock, shown to students
        when viewing courses.
        """
        context = context or {}
        context['is_author_view'] = False
        frag = self._base_view(context=context)
        frag.add_javascript_url('//app.annoto.net/annoto-bootstrap.js');
        return frag

    def _base_view(self, context=None):
        annoto_auth = self.get_annoto_settings()
        horisontal, vertical = self.get_position()
        translator = self.runtime.service(self, 'i18n').translator
        lang = getattr(
            translator,
            'get_language',
            lambda: translator.info().get('language', settings.LANGUAGE_CODE)
        )()
        rtl = getattr(translator, 'get_language_bidi', lambda: lang in settings.LANGUAGES_BIDI)()

        course = self.get_course_obj()
        course_overview = CourseOverview.objects.get(id=self.course_id)

        js_params = {
            'clientId': annoto_auth.get('client_id'),
            'horisontal': horisontal,
            'vertical': vertical,
            'tabs': self.tabs,
            'overlayVideo': self.overlay_video,
            'initialState': self.initial_state,
            'privateThread': self.discussions_scope,
            'mediaTitle': self.get_parent().display_name,
            'language': lang,
            'rtl': rtl,
            'courseId': self.course_id.to_deprecated_string(),
            'courseDisplayName': course.display_name,
            'courseDescription': course_overview.short_description,
            'courseImage': course_image_url(course),
            'demoMode': not bool(annoto_auth.get('client_id')),
        }

        context['error'] = {}
        if not annoto_auth.get('client_id'):
            context['error']['type'] = 'warning'
            context['error']['messages'] = [
                _('You did not provide annoto credentials. And you view it in demo mode.'),
                _('Please add "annoto-auth:<CLIENT_ID>:<CLIENT_SECRET>" to "Advanced Settings" > "LTI Passports"'),
            ]
        else:
            try:
                jwt.PyJWS().decode(annoto_auth.get('client_id'), verify=False)
            except:
                context['error']['type'] = 'error'
                context['error']['messages'] = [
                    _('"CLIENT_ID" is not a valid JWT token.'),
                    _('Please provide valid "CLIENT_ID" in '
                      '"Advanced Settings" > "LTI Passports" > "annoto-auth:<CLIENT_ID>:<CLIENT_SECRET>"'),
                ]
            else:
                if not annoto_auth.get('client_secret'):
                    context['error']['type'] = 'error'
                    context['error']['messages'] = [
                        _('"CLIENT_SECRET" is required when "CLIENT_ID" provided.'),
                        _('Please add "CLIENT_SECRET" to '
                          '"Advanced Settings" > "LTI Passports" > "annoto-auth:<CLIENT_ID>:<CLIENT_SECRET>"'),
                    ]

        template = Template(self.resource_string("static/html/annoto.html"))
        html = template.render(Context(context))
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/annoto.css"))
        frag.add_javascript(self.resource_string("static/js/src/annoto.js"))
        frag.initialize_js('AnnotoXBlock', json_args=js_params)
        return frag

    def get_course_obj(self):
        try:
            course = self.runtime.modulestore.get_course(self.course_id)
        except AttributeError:
            course = None
        return course

    def get_annoto_settings(self):
        """Get authorization crederntials from 'LTI Passports' field"""
        course = self.get_course_obj()
        if course:
            auth = [lp for lp in course.lti_passports if lp.startswith('annoto-auth:')]
            if auth:
                values = [v.strip() for v in auth[0].split(':')]
                return dict(zip(['name', 'client_id', 'client_secret'], values))

        return {}

    def _json_resp(self, data):
        return Response(json.dumps(data))

    def _build_absolute_uri(self, request, location):
        _django_request = HttpRequest()
        _django_request.META = request.environ.copy()
        return _django_request.build_absolute_uri(location)

    @XBlock.handler
    def get_jwt_token(self, request, suffix=''):
        """Generate JWT token for SSO authorization"""
        annoto_auth = self.get_annoto_settings()
        if not annoto_auth:
            msg = _('Annoto authorization is not provided in "LTI Passports".')
            return self._json_resp({'status': 'error', 'msg': msg})

        user = self.runtime.service(self, 'user')._django_user
        if not user:
            msg = _('Requested user does not exists.')
            return self._json_resp({'status': 'error', 'msg': msg})

        profile_name = hasattr(user, 'profile') and user.profile and user.profile.name
        name = profile_name or user.get_full_name() or user.username
        photo = self._build_absolute_uri(request, get_profile_image_urls_for_user(user)['small'])

        roles = user.courseaccessrole_set.filter(course_id=self.course_id).values_list('role', flat=True)

        if CourseStaffRole.ROLE in roles or GlobalStaff().has_user(user):
            scope = 'super-mod'
        elif CourseInstructorRole.ROLE in roles:
            scope = 'moderator'
        else:
            scope = 'user'

        payload = {
            'expire': int(time.time() + 60 * 20),
            'iss': annoto_auth['client_id'],
            'jti': user.id,
            'name': name,
            'email': user.email,
            'photoUrl': photo,
            'scope': scope
        }

        token = jwt.encode(payload, annoto_auth['client_secret'], algorithm='HS256')
        return self._json_resp({'status': 'ok', 'token': token})
