from compas_cloud.datastructures import MeshExtended
"""
from compas.datastructures import Mesh
from compas_cloud_future import CloudBase

class MeshExtended(CloudBase, Mesh):
    pass
"""

#  FUNCTION #1: CLOUD INSTANTIATION
# ==============================================================================
pmesh = MeshExtended(cloud_instance=True, cloud_dkey='mesh', cloud_port=9000)

# <class '.<< CACHED OBJECT PROXY: MeshExtended >>'>
# << CACHED OBJECT PROXY:
# {
#    "compas": "0.17.2",
#    "data": {
#    ...
#    },
#    "datatype": "compas_struct_ml_proxy._cloud/MeshExtended"
# }
# >>


# FUNCTION #2: AUTO-CLOUD-SOLVE: WRAPS ALL CALLABLE NON-STATIC/-CLASS METHODS
# ==============================================================================
mesh = MeshExtended(cloud_autosolve=True, cloud_port=9000)
# class MeshExtended(CloudBase, Mesh):
#    def dummy_numpy_using_method(self):
#        from numpy import random
#        return random.rand(3, 3).tolist()
print(mesh.dummy_numpy_using_method())
exit()
# [[0.56646419450045249, 0.65757137924650677, 0.52258317065161219], ..., ...]]


# FUNCTION #3: TO_CLOUD/FROM_CLOUD
# ==============================================================================
mesh = MeshExtended()
pmesh = mesh.to_cloud(cloud_dkey='mesh', cloud_port=9000)
pmesh.add_vertex(x=0., y=0., z=0.)
pmesh.add_vertex(x=1., y=1., z=1.)
res = pmesh.to_vertices_and_faces(cache=0)
MeshExtended.from_vertices_and_faces(*res)


mesh_ = MeshExtended.from_cloud('mesh', cloud_port=9001)
print(mesh_.vertices_attributes(names='xyz'))
# [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]