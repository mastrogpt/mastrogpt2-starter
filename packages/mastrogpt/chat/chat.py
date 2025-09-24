import os, requests as req, json
import socket, traceback, time

def url(args, cmd):
  apihost = args.get("OLLAMA_API_HOST", os.getenv("OLLAMA_API_HOST", ""))
  if apihost == "":
    base = args.get("OLLAMA_HOST", os.getenv("OLLAMA_HOST", ""))
    auth = args.get("AUTH", os.getenv("AUTH", ""))
    apihost = "https://" + auth + "@" + base
  return f"{apihost}/api/{cmd}"

def stream(args, lines, state=None):
  out = ""
  sock = None
  addr = (args.get("STREAM_HOST", ""),int(args.get("STREAM_PORT") or "0"))
  if addr[0] and addr:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    sock.connect(addr)
    #print(addr, sock)
    if state:
      buf = json.dumps(state).encode("utf-8")
      #print(buf)
      sock.sendall(buf)
      time.sleep(0.01)  # give some time to process the state

  for line in lines:
    msg = {}
    # parse lines, can be
    # a string
    # { "response" : ...} 
    # { "state": .. }
    try:
      jo = json.loads(line.decode("utf-8"))
      if "state" in jo:
        msg["state"] =  jo.get("state", "")
      if "response" in jo:
        res =jo.get("response", "")
        msg["output"] = res
        out += res
    except:
      msg["output"] = line 
      out += line
    
    if sock is not None:
        buf = json.dumps(msg).encode("utf-8") 
        #print(buf)
        sock.sendall(buf)
  if sock is not None:
    sock.close()
  return out

def ask(args, model, inp):
    msg = { "model": model, "prompt": inp, "stream": True }
    return req.post(url(args, "generate"), json=msg, stream=True).iter_lines()

def text(msg):
    for line in msg.splitlines():
        time.sleep(0.1)
        yield json.dumps({"response": line+"\n"}).encode("utf-8")

def models(args, search=None):
    msg = {}
    api = url(args, "tags")
    data = req.get(api).json()
    msg["response"] = "models available:\n"
    yield json.dumps(msg).encode("utf-8")
    for model in data.get("models", []):
      time.sleep(0.1)
      name = model.get("name", "")
      if search and name.startswith(search):
        msg["response"] = f"selected {name}\n"
        msg["state"] = name
        yield json.dumps(msg).encode("utf-8")
        break
      msg["response"] = name+"\n"
      yield json.dumps(msg).encode("utf-8")

def chat(args):
  model = args.get("state", "")
  title = args.get("title", "")
  state = {"state": model }
  print(f"state={model} title={title}")
  try: 
    inp = args.get("input", "")
    if inp == "@":
      lines = models(args)
      out = stream(args, lines, state)
    elif inp.startswith("@"):
      lines = models(args, inp[1:])
      out = stream(args, lines, state)
    elif inp != "":
      if model != "": 
        lines = ask(args, model, inp)
      else:
        lines = text("No model selected.\nPlease use @prefix to select a model.")
      out = stream(args, lines, state)
    else:
      out = "Welcome to Ollama.\nType `@` to see available models.\nType `@<model>` to select a model."

  except Exception as e:
    traceback.print_exc()
    out = f"Error: {str(e)}\n"

  return { "output": out, "streaming": True, "state": model}

