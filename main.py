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

""" main.py """

import logging
import os
import random
import time

import webapp2
from webapp2_extras.routes import RedirectRoute

from google.appengine.api import app_identity
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from basehandler import BaseHandler

compute = discovery.build(
    'compute', 'v1', credentials=GoogleCredentials.get_application_default())

DEFAULT_ZONE = 'us-central1-f'

DEFAULT_MACHINE_TYPE = 'f1-micro'

DEFAULT_IMAGE_PROJECT = 'debian-cloud'

DEFAULT_IMAGE_FAMILY = 'debian-8'

INSTANCE_NAME_TEMPLATE = "{slug}-{date}-{rand_hex4:0=4x}"

DOCKER_IMAGE_NAME = 'datetimeupload'


def get_docker_image_urn():
    """
    Gets the URN for our test image in our project specfic GCR repo
    """
    return 'gcr.io/{}/{}'.format(
        app_identity.get_application_id(), DOCKER_IMAGE_NAME)


def build_instance_name(slug):
    """
    Build a compute instance name given a (human readable) slug that includes
    the launch datetime and random component to prevent collisions

    Parameters:

    :slug: A meaning full name that describes the nature or purpose
        of the instance
    """
    if not isinstance(slug, basestring):
        raise ValueError("Invalid slug value {}".format(slug))

    return INSTANCE_NAME_TEMPLATE.format(
        slug=slug,
        date=time.strftime("%d%m%H%M"),
        rand_hex4=random.getrandbits(16)
    )


def get_instance_image_url():
    """
    Gets the URL for the bootable image that the instance will run
    """
    response = compute.images().getFromFamily(
        project=DEFAULT_IMAGE_PROJECT, family=DEFAULT_IMAGE_FAMILY
    ).execute()
    return response['selfLink']


def build_machine_type_urn(zone=DEFAULT_ZONE, machine_type=DEFAULT_MACHINE_TYPE):
    """
    Build the URN for the machineType of the instance
    """
    return 'zones/{}/machineTypes/{}'.format(zone, machine_type)

# N.B. get available machine types by executing the following on the CLI:
# gcloud compute machine-types list


def create_default_service_account(scopes=None):
    """
    Creates a instance fragment for the default service account. The global
    scope is used if an alternative list of scopes is not provided. This allows
    the instance to perform any project action.

    Keyword arguments:
    :scopes: The list of scopes that this instance can access
    """
    scopes = scopes or ['https://www.googleapis.com/auth/cloud-platform']
    return {
        'scopes': scopes,
        'email': 'default'
    }

# N.B. The default service account is consider a legacy mechanism and you
# may want to use IAM roles in production:
# https://cloud.google.com/compute/docs/access/service-accounts#accesscopesiam


# A config fragment to provide an instance with an external network interface
EXTERNAL_INTERFACE = {
    'network': 'global/networks/default',
    'accessConfigs': [
        {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
    ]
}


def build_insert_request_body(instance_name, startup_script):
    """
    Builds a compute 'insert' request given a name and a startup_script.

    Parameters:

    :instance_name: The name to be used for the instance
    :startup_script: The script to be run as the instance starts
    """
    disk_image_source = get_instance_image_url()
    return {
        'name': instance_name,
        'machineType': build_machine_type_urn(),
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': disk_image_source,
                }
            }
        ],
        'serviceAccounts': [create_default_service_account()],
        'metadata': {
            'items': [
                {
                    'key': 'startup-script',
                    'value': startup_script
                }
            ]
        },
        'networkInterfaces': [
            EXTERNAL_INTERFACE
        ]
    }


class TaskLauncher(BaseHandler):
    """ Handler for launching tasks on compute engine """

    def _launch_instance(self):
        instance_name = build_instance_name('test')
        project = app_identity.get_application_id()

        container_args = 'gs://{}.appspot.com/{}/{}.txt'.format(
            project, DOCKER_IMAGE_NAME, instance_name)

        startup_script = self.jinja2.render_template(
            'startup.sh', instance_name=instance_name,
            docker_image=get_docker_image_urn(),
            container_args=container_args,
            zone_id=DEFAULT_ZONE
        )

        request = compute.instances().insert(
            project=project, zone=DEFAULT_ZONE,
            body=build_insert_request_body(instance_name, startup_script))

        logging.info('compute insert service response %s', request.execute())
        return instance_name

    def get(self):
        """ Handle get request """
        if self.request.headers.get('X-Appengine-Cron', False):
            self._launch_instance()
            return

        self.render_response(
            'launch_form.html',
            launched=self.request.GET.get('launched'))

    def post(self):
        """ Handle post request """
        instance_name = self._launch_instance()
        self.redirect(
            self.request.path + '?launched={}'.format(instance_name))


#####################
# Application Setup #
#####################

# This part sets up the WSGI app.
# It is a little more involved than usual because we are trying to
# setup a cookie secret without storing it in git.


def on_dev_server():
    """ Return true if we are running on dev_appserver"""
    return os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')


def get_project_metadata(metadata_key):
    """
    Get a project metadata value by key

    Parameters:

    :metadata_key: key for the value to fetch
    """
    project_id = app_identity.get_application_id()
    project = compute.projects().get(project=project_id).execute()
    for entry in project['commonInstanceMetadata']['items']:
        if entry['key'] == metadata_key:
            print type(entry['value'])
            return entry['value']
    return None


def get_cookie_secret_error():
    """ Return the appropriate error message if secrets have not been setup"""
    target = 'secrets' if on_dev_server() else 'cloud_secrets'
    return 'ERROR: Cookie secret not set, run "make {}"'.format(target)


def get_dev_secrets():
    """
    Get secrets used when developing locally.
    """

    cookie_secret = None
    try:
        import _dev
        cookie_secret = _dev.secrets['cookie_secret']
    except ImportError:
        pass
    return cookie_secret


def get_application(routes):
    """
    Return a configured webapp2 WSGI app if secrets have been setup properly.
    Otherwise return a trivial 'error' WSGI app if not.

    Parameters:

    :routes: webapp2 routes
    """
    cookie_secret = None
    if not on_dev_server():
        cookie_secret = get_project_metadata('cookie_secret')
    else:
        cookie_secret = get_dev_secrets()

    config = {}
    config['webapp2_extras.sessions'] = {
        'secret_key': str(cookie_secret),
    }

    if cookie_secret:
        return webapp2.WSGIApplication(routes=routes, config=config)
    else:
        return error_app(get_cookie_secret_error())


def error_app(msg):
    """
    A trivial WSGI app that always displays a 500 error with a given message

    Parameters:

    :msg: The message to display in the response body with the 500 error
    """
    def _app(_, start_response):
        response_body = msg
        status = '500 Error'
        response_headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(response_body)))
        ]
        start_response(status, response_headers)
        return [response_body]
    return _app


app = get_application([
    RedirectRoute('/', redirect_to='/launcher'),
    ('/launcher', TaskLauncher),
])
