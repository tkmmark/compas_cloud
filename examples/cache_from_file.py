
import compas
from compas_cloud import Proxy

p = Proxy()

file_path = compas.get('hypar.obj')
pmesh = p.cache_from_file(file_path, method='from_obj', dtype='compas.datastructures/Mesh')

print(type(pmesh))