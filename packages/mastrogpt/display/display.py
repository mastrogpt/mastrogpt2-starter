import chevron
import chess, chess.svg
import traceback
import os
import boto3

def render(src, args):
    with open(src) as f:
        return chevron.render(f, args)
    
def board(args):
    fen = args['chess']
    try: 
        print(fen)
        board = chess.Board(fen)
        data = {"html": chess.svg.board(board=board) }
        out = render("html.html", data)
    except Exception as e:
        data =  {"title": "Bad Chess Position", "message": str(e)}
        out = render("message.html", data)
        traceback.print_exc()

    return out
    
def s3client(args):
    base = args.get("S3_API_URL")
    key = args.get("S3_ACCESS_KEY", os.getenv("S3_ACCESS_KEY"))
    sec = args.get("S3_SECRET_KEY", os.getenv("S3_SECRET_KEY"))
    bucket = args.get("S3_BUCKET_DATA", os.getenv("S3_BUCKET_DATA"))
    client = boto3.client('s3', region_name='us-east-1', endpoint_url=base, aws_access_key_id=key, aws_secret_access_key=sec )
    return client, bucket

def s3url(client, bucket, path):
    return client.generate_presigned_url('get_object',
        Params={
            'Bucket': bucket,
            'Key': path
        },
        ExpiresIn=3600  # Valid for 1 hour
    )

 
def display(args):
    print(args)
    out = "No content specified."

    if "html" in args:
        out = render("html.html", args)
    elif "iframe" in args:
        print(args.get("BASE", ""), args.get("iframe", ""))
        out = render("iframe.html", args)
    elif "code" in args:
        data = {
            "code": args['code'],
            "language": args.get("language", "plain_text")
        }
        out = render("editor.html", data)
    elif "chess" in args:
        out = board(args)
    elif "message" in args:
        if not "title" in args:
            args["title"] = "Message"
        out = render("message.html", args)
    elif "images" in args:
        images = args.get("images", "").strip().split(",")
        out = ""
        client, bucket = s3client(args)
        for image in images:
            print(image)
            url = s3url(client, bucket, image)
            out += f'<img src="{url}" /><br>'

        data = {"html": out}
        out = render("html.html", data)

    code = 200 if out != "" else 204
    return {
        "body": out,
        "statusCode": code,
        "headers": {
            "Content-Security-Policy": "frame-ancestors: *;"
        }
    }

