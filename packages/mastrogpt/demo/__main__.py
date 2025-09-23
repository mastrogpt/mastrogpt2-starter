#--kind python:default
#--web true
#--annotation index '80:Demo:Demo::'

import demo
def main(args):
  return { "body": demo.demo(args) }
