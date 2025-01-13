import json

def error(out_obj):
    return {
        "statusCode": 400,
        "success": False,
        "body": json.dumps(out_obj)
    }

def success(out_obj):
    return {
        "statusCode": 200,
        "success": True,
        "body": json.dumps(out_obj)
    }