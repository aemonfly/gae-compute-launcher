# Google App Engine Compute Launcher

A demonstration of how to launch docker based tasks on Google Compute Engine
using Google App Engine.

## Running on DevAppServer

Run the following:

    make dev

Or if you wish to run dev_appserver.py directly

    make secrets
    dev_appserver -A your-project-id app.yaml

You must specify your cloud project in `your-project-id` if you actually want
to launch instances on google cloud from dev_appserver.py.

Now navigate to the page `http://localhost:8080/launcher`

## Running on AppEngine

Ensure you have setup gcloud CLI to point to the right application id:

    gcloud config set project your-project-id

First you have to create a cookie secret and store in your appengine project
metadata. We will do this by setting 'cookie_secret' as a metadata attribute
of the current google cloud project. You can do this by running:

    make cloud_secrets

Now you can deploy the app:

    make deploy

Now navigate to `http://your-project-id.appspot.com/launcher`.

## License and Disclaimer

This is an example provided 'as-is' without any warrantee see LICENSE.txt for
details.