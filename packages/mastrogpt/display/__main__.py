#--web true
#--kind python:default
#--param S3_API_URL "$S3_API_URL"
#--param S3_ACCESS_KEY $S3_ACCESS_KEY
#--param S3_SECRET_KEY $S3_SECRET_KEY
#--param S3_BUCKET_DATA $S3_BUCKET_DATA
#--param BASE "$OPSDEV_HOST"

import display
def main(args):
    return display.display(args)
