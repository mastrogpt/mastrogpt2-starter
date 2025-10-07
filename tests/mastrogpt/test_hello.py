import sys 
sys.path.append("packages/mastrogpt/demo")
import demo

def test_demo():
    res = demo.demo({})
    assert res["output"] == "demo"
