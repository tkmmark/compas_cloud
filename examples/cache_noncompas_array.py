
from compas_cloud import Proxy

p = Proxy()

ar = [[1, 3], [2, 4], [3, 5]]
ar1 = p.cache(ar, dkey='ar1', as_type='numpy/array')

ar2 = ar1.transpose(dkey='ar2', cache=2)
print(ar2)
"""
<< CACHED OBJECT PROXY:
[[1 2 3]
 [3 4 5]]
>>
"""

p.set_cache_protocol(2)
ar3 = ar1.dot(ar2)
print(ar3)
"""
<< CACHED OBJECT PROXY:
[[10 14 18]
 [14 20 26]
 [18 26 34]]
>>
"""

ar4 = ar3 + ar3
print(ar4)
"""
< PROXY CACHED OBJECT :
[[20 28 36]
 [28 40 52]
 [36 52 68]] >
"""