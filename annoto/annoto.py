import jwt
import time
import json
import logging
from webob import Response
from django.conf import settings
from django.http.request import HttpRequest
from django.template import Context, Template
from django.contrib.auth.models import User

import pkg_resources
from xblock.core import XBlock
from xblock.fields import Scope, String, Boolean
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.lib.courses import course_image_url
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole, GlobalStaff

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

    video_block_id = String(
        display_name=_("Video ID"),
        help=_("This is the component ID for the video in which you want Annoto to appear."),
        default=None,
    )

    widget_position = String(
        display_name=_("Widget Position"),
        values=(
            {'display_name': _('top-left'), 'value': 'left-top'},
            {'display_name': _('top-right'), 'value': 'right-top'},
            {'display_name': _('left'), 'value': 'left-center'},
            {'display_name': _('right'), 'value': 'right-center'},
            {'display_name': _('bottom-left'), 'value': 'left-bottom'},
            {'display_name': _('bottom-right'), 'value': 'right-bottom'}
        ),
        default="right-top",
    )

    object_type = String(
        display_name=_("Learning Object Type"),
        values=(
            {'display_name': _('Video'), 'value': 'openedx'},
            {'display_name': _('Page'), 'value': 'page'},
        ),
        default="openedx",
    )

    overlay_video = Boolean(
        display_name=_("Overlay Video"),
        default=False
    )

    tabs = String(
        display_name=_("Tabs"),
        values=(
            {'display_name': _('Enabled'), 'value': 'enabled'},
            {'display_name': _('Hidden'), 'value': 'hidden'},
            {'display_name': _('Auto'), 'value': 'auto'},
        ),
        default="enabled",
    )

    initial_state = String(
        display_name=_("Initial State"),
        values=(
            {'display_name': _('Auto'), 'value': 'auto'},
            {'display_name': _('Open'), 'value': 'open'},
            {'display_name': _('Closed'), 'value': 'closed'}
        ),
        default="open",
    )

    discussions_scope = String(
        display_name=_('Discussions Scope'),
        values=(
            {'display_name': _('Private per course cohort'), 'value': 'cohort'},
            {'display_name': _('Private per course'), 'value': 'course'},
            {'display_name': _('Site Wide'), 'value': 'site'},
        ),
        default='cohort'
    )

    video_type = String(
        display_name=_("Video Type"),
        values=(
            {'display_name': _('Video On-Demand'), 'value': 'ondemand'},
            {'display_name': _('Live Streaming'), 'value': 'stream'},
        ),
        default="ondemand",
    )

    features = String(
        display_name=_("Features"),
        values=(
            {'display_name': _('Comments & Notes'), 'value': 'comments_and_notes'},
            {'display_name': _('Comments'), 'value': 'comments'},
            {'display_name': _('Private Notes'), 'value': 'notes'},
            {'display_name': _('Only Analytics'), 'value': 'only_analytics'},
        ),
        default="comments_and_notes",
    )

    editable_fields = (
        'display_name', 'object_type', 'video_block_id', 'widget_position', 'overlay_video',
        'tabs', 'initial_state', 'discussions_scope', 'video_type', 'features',
    )

    has_author_view = True

    @property
    def i18n_service(self):
        """ Obtains translation service """
        i18n_service = self.runtime.service(self, "i18n")
        if i18n_service:
            return i18n_service
        else:
            return type('DummyTranslationService', (object,), {'gettext': _})()

    @staticmethod
    def resource_string(path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def get_position(self):
        """Parse 'widget_position' field"""
        return self.widget_position.split('-')

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
        frag.add_javascript_url('//app.annoto.net/annoto-bootstrap.js')
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        context = {
            'fields': [],
            'xblock_version': pkg_resources.require('annoto-xblock')[0].version
        }
        # Build a list of all the fields that can be edited:
        for field_name in self.editable_fields:
            field = self.fields[field_name]
            assert field.scope in (Scope.content, Scope.settings), (
                "Only Scope.content or Scope.settings fields can be used with "
                "StudioEditableXBlockMixin. Other scopes are for user-specific data and are "
                "not generally created/configured by content authors in Studio."
            )
            field_info = self._make_field_info(field_name, field)
            if field_info is not None:
                context["fields"].append(field_info)

        template = Template(self.resource_string("static/html/studio_edit.html"))
        fragment = Fragment(template.render(Context(context)))
        fragment.add_javascript(self.resource_string('static/js/src/studio_edit.js'))
        fragment.initialize_js('StudioEditableXBlockMixin')

        return fragment

    def _base_view(self, context=None):
        context = context is None and {'is_author_view': False} or context
        annoto_auth = self.get_annoto_settings()
        horizontal, vertical = self.get_position()
        translator = self.runtime.service(self, 'i18n').translator
        lang = getattr(
            translator,
            'get_language',
            lambda: translator.info().get('language', settings.LANGUAGE_CODE)
        )()
        rtl = getattr(translator, 'get_language_bidi', lambda: lang in settings.LANGUAGES_BIDI)()

        course = self.get_course_obj()
        course_overview = CourseOverview.objects.get(id=self.course_id)

        course_id = str(self.course_id)
        course_display_name = course.display_name
        user = self._get_user()
        if not context['is_author_view'] and user and self.discussions_scope == 'cohort':
            from openedx.core.djangoapps.course_groups.cohorts import get_cohort
            cohort = get_cohort(user, self.course_id)
            if cohort:
                course_id = u'{}_{}'.format(course_id, cohort.id)
                course_display_name = u'{} [{}]'.format(course_display_name, cohort.name)

        js_params = {
            'objectType': self.object_type,
            'clientId': annoto_auth.get('client_id'),
            'horizontal': horizontal,
            'vertical': vertical,
            'tabs': self.tabs,
            'overlayVideo': self.overlay_video,
            'initialState': self.initial_state,
            'privateThread': self.discussions_scope != 'site',
            'mediaTitle': self.get_parent().display_name,
            'language': lang,
            'rtl': rtl,
            'courseId': course_id,
            'courseDisplayName': course_display_name,
            'courseDescription': course_overview.short_description,
            'courseImage': course_image_url(course),
            'demoMode': not bool(annoto_auth.get('client_id')),
            'isLive': self.video_type == 'stream',
            'comments': 'comments' in self.features,
            'privateNotes': 'notes' in self.features,
            'videoBlockID': self.video_block_id,
        }

        context['error'] = {}
        if not annoto_auth.get('client_id'):
            context['error']['type'] = 'warning'
            context['error']['messages'] = [
                self.i18n_service.gettext('You did not provide annoto credentials. And you view it in demo mode.'),
                self.i18n_service.gettext('Please add "annoto-auth:<CLIENT_ID>:<CLIENT_SECRET>" to "Advanced Settings" > "LTI Passports"'),
            ]
        else:
            try:
                jwt.PyJWS().decode(annoto_auth.get('client_id'), verify=False)
            except:
                context['error']['type'] = 'error'
                context['error']['messages'] = [
                    self.i18n_service.gettext('"CLIENT_ID" is not a valid JWT token.'),
                    self.i18n_service.gettext('Please provide valid "CLIENT_ID" in '
                      '"Advanced Settings" > "LTI Passports" > "annoto-auth:<CLIENT_ID>:<CLIENT_SECRET>"'),
                ]
            else:
                if not annoto_auth.get('client_secret'):
                    context['error']['type'] = 'error'
                    context['error']['messages'] = [
                        self.i18n_service.gettext('"CLIENT_SECRET" is required when "CLIENT_ID" provided.'),
                        self.i18n_service.gettext('Please add "CLIENT_SECRET" to '
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

    @staticmethod
    def _json_resp(data):
        return Response(json.dumps(data))

    @staticmethod
    def _build_absolute_uri(request, location):
        _django_request = HttpRequest()
        _django_request.META = request.environ.copy()
        return _django_request.build_absolute_uri(location)

    def _get_user(self):
        user = User.objects.filter(
            id=self.runtime.service(self, 'user').get_current_user().opt_attrs.get('edx-platform.user_id')
        ).first()
        return user

    @XBlock.handler
    def get_jwt_token(self, request, suffix=''):
        """Generate JWT token for SSO authorization"""
        annoto_auth = self.get_annoto_settings()
        if not annoto_auth:
            msg = self.i18n_service.gettext('Annoto authorization is not provided in "LTI Passports".')
            return self._json_resp({'status': 'error', 'msg': msg})

        user = self._get_user()
        if not user:
            msg = self.i18n_service.gettext('Requested user does not exists.')
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
            'exp': int(time.time() + 60 * 20),
            'iss': annoto_auth['client_id'],
            'jti': user.id,
            'name': name,
            'email': user.email,
            'photoUrl': photo,
            'scope': scope
        }

        token = jwt.encode(payload, annoto_auth['client_secret'], algorithm='HS256')
        return self._json_resp({'status': 'ok', 'token': getattr(token, 'decode', lambda: token)()})
