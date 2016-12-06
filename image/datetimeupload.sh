#!/bin/bash
gcs_path=$1
if [ -z "$gcs_path" ]; then
    echo 'Error: required gcs_path argument missing'
    exit 1
fi

## Generate GCS config file on the fly
METADATA_ENDPOINT="http://metadata.google.internal/computeMetadata/v1"

numeric_project_id=$(curl $METADATA_ENDPOINT/project/numeric-project-id)

cat <<EOF > /etc/boto.cfg
[GSUtil]
default_project_id = $numeric_project_id
default_api_version = 2
[GoogleCompute]
service_account = default
[Plugin]
plugin_directory = /usr/lib/python2.7/dist-packages/google_compute_engine/boto
EOF
## Finish generating GCS config file

current_date=$(date)
tempfile=$(mktemp)

cat <<EOF > "$tempfile"
${current_date}
EOF

/gsutil/gsutil copy $tempfile $gcs_path
/gsutil/gsutil setmeta -h "Content-Type:text/plain" $gcs_path

rm $tempfile
