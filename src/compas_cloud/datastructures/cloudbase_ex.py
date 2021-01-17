
from compas.datastructures import Mesh
from compas_cloud.datastructures.cloudbase import CloudBase

class MeshExtended(CloudBase, Mesh):
    def dummy_numpy_using_method(self):
        from numpy import random
        return random.rand(3, 3).tolist()