from compas.datastructures import Mesh
from compas_cloud import Proxy

p = Proxy()

mesh = Mesh()
pmesh = p.cache(mesh)

print(pmesh)
