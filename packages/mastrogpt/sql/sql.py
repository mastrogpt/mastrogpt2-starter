import os
import psycopg

def to_html(result):
    """
    If result is a dict with a single key, 
    If it is not select return {"output": f"{key}: {value}"}
    Otherwise build and html table with the value of the select key, assuming it is a list of dicts
    and return {"output": "found <count> rows", "html": <the html table> }
    """
    if not isinstance(result, dict) or len(result) != 1:
        return {"output": "Invalid result format"}
    
    key = list(result.keys())[0]
    value = result[key]
    
    if key != "select":
        return {"output": f"{key}: {value}"}
        
    if not isinstance(value, list):
        return {"output": "Invalid select result format"}
        
    rows = value
    if not rows:
        return {"output": "found 0 rows"}
        
    columns = list(rows[0].keys())
    html = '<table border="1"><thead><tr>'
    html += ''.join(f'<th>{col}</th>' for col in columns)
    html += '</tr></thead><tbody>'
    
    for row in rows:
        html += '<tr>'
        html += ''.join(f'<td>{row[col]}</td>' for col in columns)
        html += '</tr>'
    html += '</tbody></table>'
    
    return {
        "output": f"found {len(rows)} rows",
        "html": html
    }
    
def query(dburl, sql):
    conn = None
    cur = None
    cmd = sql.strip().lower().split()[0]
    result = "unknown statement"
    try:
        conn = psycopg.connect(dburl)
        cur = conn.cursor()
        cur.execute(sql)
        if cmd == "select":
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            # Convert rows to list of dicts
            result = [dict(zip(columns, row)) for row in rows]
        elif cmd == "create":
            result = cur.statusmessage
        else:
            row_count = cur.rowcount
            result = f"affected rows: {row_count}"
        
        conn.commit()
    except Exception as e:
        result = str(e)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return {cmd: result }

def sql(args):
    dburl = args.get("POSTGRES_URL", os.getenv("POSTGRES_URL"))
    sql = args.get("input", "")
    res =  {"Welcome": "specify a SQL query or '@' to list tables"}
    if sql != "":
        if sql == "@":
            lines = ["select table_schema, table_name from information_schema.tables where table_type = 'BASE TABLE' and table_schema not in ('pg_catalog', 'information_schema')"]
        else: 
            lines = sql.split("\n")
        if len(lines) == 1:
            res = query(dburl, lines[0])
        else:
            #print(lines)
            for line in lines:
                print(line)
                res = query(dburl, line)
                print(res)
            res = {"multiple": f"executed {len(lines)} statements"}

    if "__ow_method" in args:
        res = to_html(res)

    return res

