
from compas_cloud import Proxy

p = Proxy()

p.run("print('hello world')")

p.run("from numpy import array")
p.run("a = array([1., 2., 3.])")
p.run("b = a.dot(a.T)")

p.run("from pprint import pprint")
p.run("pprint(_server.logs)")