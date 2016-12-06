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

.PHONY: deps image deploy lint secrets clean_secrets cron

SDK_ROOT = $(shell gcloud --format='value(installation.sdk_root)' info)
APPCFG = $(SDK_ROOT)/platform/google_appengine/appcfg.py
PROJECT_ID = $(shell gcloud config list --format 'value(core.project)')
COOKIE_SECRET = $(shell python -c 'import base64, os; print base64.b64encode(os.urandom(16))')
IMAGE_NAME = "datetimeupload"
USER = $(shell whoami)

define DEV_SECRETS
""" dev secrets """

secrets = {
    'cookie_secret': "$(COOKIE_SECRET)"
}
endef

lib/: requirements.txt
	pip install --upgrade -r requirements.txt -t lib

deps: lib/

export DEV_SECRETS
_dev.py:
	@echo "$$DEV_SECRETS" > _dev.py

secrets: _dev.py

clean_secrets:
	rm -f _dev.py

dev: secrets deps
	dev_appserver.py -A $(PROJECT_ID) app.yaml

cloud_secrets:
	@echo gcloud compute project-info add-metadata --metadata "cookie_secret=***********"
	@gcloud compute project-info add-metadata --metadata "cookie_secret=$(COOKIE_SECRET)"

image:
	pushd image && docker build . -t "$(USER)/datetimeupload"  && \
		docker tag "$(USER)/$(IMAGE_NAME)" \
			"gcr.io/$(PROJECT_ID)/$(IMAGE_NAME)" && \
		gcloud docker -- push "gcr.io/$(PROJECT_ID)/$(IMAGE_NAME)" && \
		popd

deploy: deps
	gcloud -q app deploy --stop-previous-version -v 1 app.yaml

cron:
	@echo appcfg.py update_cron .
	@$(APPCFG) -A $(PROJECT_ID) update_cron .

lint: deps
	python -m flake8 && python -m pylint *.py
