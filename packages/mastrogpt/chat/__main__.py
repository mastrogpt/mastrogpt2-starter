#--kind python:default
#--web true
#--param OLLAMA_API_HOST "${OLLAMA_PROTO:-https}://${OLLAMA_AUTH:-${AUTH}}@$OLLAMA_HOST"
#--annotation index '80:Demo:Chat:pinocchio:'

import chat
def main(args):
  return { "body": chat.chat(args) }
