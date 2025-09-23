#--kind python:default
#--web true
#-a index 80:Demo:Hello::
import hello
def main(args):
  return { "body": hello.hello(args) }
