#--kind python:default
#--web true
#--param OLLAMA_API_HOST "https://$AUTH@$OLLAMA_HOST"
#--param OLLAMA_CHAT_MODEL "$OLLAMA_CHAT_MODEL"
#--annotation index '80:Demo:Chat:demo,admin:'

import chat
def main(args):
  return { "body": chat.chat(args) }
