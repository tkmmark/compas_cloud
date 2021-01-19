from compas.datastructures import Mesh
from compas_cloud import Proxy

p = Proxy()

mesh = Mesh()

pform = p.cache(mesh, as_type='compas_tna.diagrams/FormDiagram')

print(type(mesh))
print(type(pform))
