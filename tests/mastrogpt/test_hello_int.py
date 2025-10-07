import os, requests as req
def test_demo():
    url = os.environ.get("OPSDEV_HOST") + "/api/my/mastrogpt/demo"
    res = req.get(url).json()
    assert res.get("output") == "demo"
