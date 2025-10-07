#--kind python:default
#--web true
#--param "OLLAMA_HOST" "$OLLAMA_HOST"
#--param "OLLAMA_PROTO" "$OLLAMA_PROTO"
#--param "AUTH" "$AUTH"
#--annotation index '80:Demo:Ollama:pinocchio:'

import chat
def main(args):
  return { "body": chat.chat(args) }

