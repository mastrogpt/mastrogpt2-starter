#--kind python:default
#--web true
#-a provide-api-key true
#--param OPSDEV_APIHOST "$OPSDEV_APIHOST"
#--param OPSDEV_USERNAME "$OPSDEV_USERNAME"
#--param OPSDEV_HOST "$OPSDEV_HOST"

import index
def main(args):
  return  {"body": index.main(args) }
