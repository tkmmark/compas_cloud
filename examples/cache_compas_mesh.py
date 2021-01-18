from compas.datastructures import Mesh
from compas_cloud import Proxy

p = Proxy()

mesh = Mesh()
pmesh = p.cache(mesh, as_type='compas.datastructures/Mesh')

print(pmesh)
