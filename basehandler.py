# ISC License
#
# Copyright (c) 2016, Frank A. J. Wilson
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

""" basehandler.py """

import base64
import os

import webapp2

from webapp2_extras import jinja2, sessions

# Follows OWASP recommendation
# https://www.owasp.org/index.php/Insufficient_Session-ID_Length
CSRF_TOKEN_BYTES = 16

CSRF_TOKEN_DICT_KEY = '_csrf_token'

SAFE_METHODS = ['HEAD', 'GET', 'OPTIONS', 'TRACE']


class BaseHandler(webapp2.RequestHandler):
    """ BaseHandler that handles template rendering and CSRF protection """

    def __init__(self, *args, **kwargs):
        webapp2.RequestHandler.__init__(self, *args, **kwargs)
        self.session_store = None

    def is_task_queue_request(self):
        """ Checks if the request was initiated by the AppEngine task queue"""
        return 'X-AppEngine-QueueName' in self.request.headers

    def is_unsafe_request(self):
        """ Checks if the request is not using a 'safe' method """
        return self.request.method not in SAFE_METHODS

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)

        try:
            if self.is_unsafe_request() and not self.is_task_queue_request():
                if self.request.params[CSRF_TOKEN_DICT_KEY] != self.csrf_token:
                    del self.session[CSRF_TOKEN_DICT_KEY]
                    self.abort(403, 'CSRF token missing')

            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        """ Returns a session using the default cookie key. """
        return self.session_store.get_session()

    @webapp2.cached_property
    def csrf_token(self):
        """
        Gets a CSRF token stored in the session or generates one if is not set
        """
        if CSRF_TOKEN_DICT_KEY not in self.session:
            self.session[CSRF_TOKEN_DICT_KEY] = base64.b64encode(
                os.urandom(CSRF_TOKEN_BYTES))
        return self.session[CSRF_TOKEN_DICT_KEY]

    @webapp2.cached_property
    def jinja2(self):
        """ Returns a Jinja2 renderer cached in the app registry. """
        return jinja2.get_jinja2(app=self.app)

    def render_response(self, _template, **context):
        """ Renders a template and writes the result to the response. """
        context.update({CSRF_TOKEN_DICT_KEY: self.csrf_token})
        render_value = self.jinja2.render_template(_template, **context)
        self.response.write(render_value)
