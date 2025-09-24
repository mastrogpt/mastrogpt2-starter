#--kind python:default
#--web true
#--param "OLLAMA_API_HOST" "$OLLAMA_API_HOST"
#--param "OLLAMA_HOST" "$OLLAMA_HOST"
#--param "AUTH" "$AUTH"
#--annotation index '80:Demo:Ollama:pinocchio:'

import chat
def main(args):
  return { "body": chat.chat(args) }
