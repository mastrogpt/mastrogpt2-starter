import os, requests as req
from pymilvus import MilvusClient, DataType, Function, FunctionType
import hashlib, struct

DIMENSION_TEXT=4096
LIMIT=10

class VectorDB:

  def __init__(self, args, collection):
      uri = f"http://{args.get("MILVUS_HOST", os.getenv("MILVUS_HOST"))}"
      token = args.get("MILVUS_TOKEN", os.getenv("MILVUS_TOKEN"))    
      db_name = args.get("MILVUS_DB_NAME", os.getenv("MILVUS_DB_NAME"))
      self.client =  MilvusClient(uri=uri, token=token, db_name=db_name)
      self.setup(collection)

  def destroy(self, collection):
    self.client.drop_collection(collection)
    out = f"Dropped {collection}\n"
    if collection == self.collection:
      return out + self.setup(collection)
    return out

  def setup(self, collection):
    self.collection = collection    
    ls = self.client.list_collections()
    if not collection in ls:
      schema = self.client.create_schema()
      schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
      schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=DIMENSION_TEXT, enable_analyzer=True)
      schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
      bm25_function = Function(name="text_bm25_emb", input_field_names=["text"], output_field_names=["sparse"], function_type=FunctionType.BM25)
      schema.add_function(bm25_function)

      index_params = self.client.prepare_index_params()
      index_params.add_index(
          field_name="sparse",
          index_type="SPARSE_INVERTED_INDEX",
          metric_type="BM25",
          params={ "inverted_index_algo": "DAAT_MAXSCORE", "bm25_k1": 1.2, "bm25_b": 0.75}
        )
      self.client.create_collection(collection_name=self.collection, schema=schema, index_params=index_params)
      ls.append(collection)
      print("collection_name=", self.collection)

    res =  f"Collections: {" ".join(ls)}\nCurrent: {self.collection}" 
    count = self.count()
    res += f"\nCount: {count}"
    return res
  
  def insert(self, text):
    try:
      sha256 = hashlib.sha256(text.encode('utf-8')).digest()
      int64_val = struct.unpack('>q', sha256[:8])[0]  # '>q' = big-endian signed 64-bit
      res = self.client.insert(self.collection, {"text":text, "id":int64_val })
      n = res.get('insert_count', 0)
      ids = [str(x) for x in res.get('ids', [])]
      out = f"Inserted {n}: {",".join(ids)})"
      return out
    except Exception as e:
      return(f"Error: {str(e)}")
  
  def count(self):
    MAX="10000"
    count = "0"
    try:
      res = self.client.query(collection_name=self.collection, output_fields=["id"], limit=int(MAX))
      count = str(len(res))
      if count == MAX:
        count = "more than {count}"
    except Exception as e:
      pass
    return count

  def full_text_search(self, query, limit=LIMIT):
    search_params = { 'params': {'drop_ratio_search': 0.2} }
    hits = self.client.search(collection_name=self.collection, 
      limit=limit, search_params=search_params,
      data=[query], anns_field='sparse', output_fields=['text'])
    out = []
    for hit in hits:
      #hit = hits[0]  # Get the first hit
      for rec in hit:
        #rec = hit[0]
        dist = rec.get('distance', 0.0)
        text = rec.get('entity', {}).get('text', "")
        out.append((dist, text))
    return out

  def substring_search(self, search, limit=LIMIT):
    cur = self.client.query_iterator(collection_name=self.collection, 
              batchSize=2, output_fields=["id", "text"])
    res = cur.next()
    out = []
    while len(res) > 0:
      for ent in res:
        text = ent.get('text', "")
        if text.find(search) != -1:
          out.append((ent.get('id'), text))
      res = cur.next()
    return out

  def remove_by_substring(self, inp):
    cur = self.client.query_iterator(collection_name=self.collection, 
              batchSize=2, output_fields=["text"])
    res = cur.next()
    ids = []
    while len(res) > 0:
      for ent in res:
        if ent.get('text', "").find(inp) != -1:
          ids.append(ent.get('id'))
      res = cur.next()
    if len(ids) >0:
      res = self.client.delete(collection_name=self.collection, ids=ids)
      return res['delete_count']
    return 0
