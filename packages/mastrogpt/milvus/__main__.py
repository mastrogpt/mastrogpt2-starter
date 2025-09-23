#--kind python:default
#--web true
#--annotation index '90:Utils:Milvus:admin:'

#--param MILVUS_HOST "$MILVUS_HOST"
#--param MILVUS_PORT "$MILVUS_PORT"
#--param MILVUS_DB_NAME "$MILVUS_DB_NAME"
#--param MILVUS_TOKEN "$MILVUS_TOKEN"

import loader
def main(args):
  try:
    return { "body": loader.loader(args) }
  except Exception as e:
    return { "body": {"output": str(e)} }

