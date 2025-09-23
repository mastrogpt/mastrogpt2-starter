#--kind python:default
#--web true
#--annotation index '90:Utils:SQL:admin:'

#-p POSTGRES_URL "$POSTGRES_URL"
#-p REDIS_URL "$REDIS_URL"
#-p REDIS_PREFIX "$REDIS_PREFIX"

import sql
def main(args):
  # invoked by the web service
  if "__ow_method" in args:
    import os, redis
    token = args.get("token", "_:_")
    #print(token)
    [user, secret] = token.split(":")
    rd = redis.from_url(args.get("REDIS_URL"))
    check = rd.get(f"{args.get("REDIS_PREFIX")}TOKEN:{user}") or b''
    #print(check)
    if check.decode() == secret:
        return { "body": sql.sql(args) }
    return {"body": "unauthorized"}
  
  # invoked by the CLI
  return sql.sql(args) 
