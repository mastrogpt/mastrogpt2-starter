import os, json, requests
from pathlib import Path
from urllib.parse import urlparse, urlunparse

def invoke(cmd, data=None):
  apihost = os.getenv("__OW_API_HOST") or os.getenv("OPSDEV_APIHOST")
  [user, pasw] = (os.getenv("__OW_API_KEY") or os.getenv("AUTH")).split(":")
  auth = requests.auth.HTTPBasicAuth(user, pasw)
  url = f"{apihost}/api/v1/namespaces/_/{cmd}"
  #print(url)
  if data:
    res = requests.post(url, auth=auth, json=data).json()
  else:
    res = requests.get(url, auth=auth).json()
  return res

def get_indexes(actions):
  out = []
  for ent in actions:
    #ent = actions[0]
    action = ent['namespace'].split("/")[-1] + "/" + ent['name']
    anns = ent.get('annotations', [])
    for kv in anns:
        #kv = ann[0]
        if kv['key'] == 'index':
            out.append(f"{action}:{kv['value']}")
  return out

def get_services(indexes):
  smap = {}
  for index in indexes:
    #index = indexes[0]
    try:
      [action, weight, folder, name, users, iframe] = index.split(":")
    except Exception as e:
      print(f"Bad format of index {index}: should be 'action:weight:folder:name:users:iframe'")
      continue
    key = f"{weight:0>5}:{folder}"
    item = {
      "url": action,
      "name": name,
      "iframe": iframe,
    }
    if users.strip() != "":
      item['users'] = users

    if not key in smap: smap[key] = []
    smap[key].append(item)
    # final result
    res = []
    keys = list(smap.keys())
    keys.sort()
    for k in keys:
      key =k.split(":", maxsplit=1)[-1]
      res.append({key: smap[k]})
  return res

# support for legacy file based menus
def legacy(services):
  current_dir = os.path.dirname(os.path.abspath(__file__))
  files = os.listdir(current_dir)
  files.sort()
  for file in files:
    # file = files[1]
    if not file.endswith(".json"):
      continue
    print(file)
    entry = file.rsplit(".", maxsplit=1)[0].split("-", maxsplit=1)[-1]
    dict = json.loads(Path(os.path.join(current_dir, file)).read_text())
    for service in services:
      # service = services[2]
      print(service)
      if entry in service:
        for key in dict:
          key["iframe"] = ""
          service[entry].append(key)
        dict = None
        break
    if dict:
      for key in dict:
        key["iframe"] = ""
      services.append({entry: dict})
  return services  
      
def main(args):

  actions = invoke("actions")
  indexes = get_indexes(actions)
  services = get_services(indexes)
  services = legacy(services)

  username = args.get("OPSDEV_USERNAME", os.getenv("OPSDEV_USERNAME", ""))
  host = args.get("OPSDEV_HOST", os.getenv("OPSDEV_HOST", ""))
  apihost = args.get("OPSDEV_APIHOST", os.getenv("OPSDEV_APIHOST", ""))
  
  url = urlparse(apihost)
  s3_host = urlunparse(url._replace(netloc="s3."+url.netloc))
  stream_host = urlunparse(url._replace(netloc="stream."+url.netloc))

  res = {
    "username": username,
    "host": host,
    "apihost": apihost,
    "s3": s3_host,
    "streamer": stream_host,
    "services": services
  }
  return  res  