"""SYNTHETIC GRAPHICS TEST ONLY. These meshes do not depict anatomical shapes.
Names are parser/knowledge matching fixtures. NEVER embed in production HTML.
"""
import json,struct,math

def glb():
    pos=[];ind=[];rings=14;seg=24
    for j in range(rings+1):
        phi=j/rings*math.pi
        for i in range(seg+1):
            t=i/seg*2*math.pi
            pos += [.38*math.sin(phi)*math.cos(t),.7*math.cos(phi),.25*math.sin(phi)*math.sin(t)]
    for j in range(rings):
        for i in range(seg):
            a=j*(seg+1)+i;b=a+seg+1
            ind += [a,b,a+1,a+1,b,b+1]
    nodes=[{'name':'TEST_ONLY_NOT_ANATOMY_root','children':list(range(1,10))}]
    for name,xyz in [('Left humerus',[-1,1,0]),('Left ulna',[-1,-.5,0]),('Left radius',[-.3,-.5,0]),('Left scapula',[0,1,0]),('Right humerus',[1,1,0]),('Left femur',[1,-.5,0]),('Left tibia',[1,-2,0]),('Left patella',[1,-1.35,.35]),('Lumbar vertebra L4',[0,-2,0])]:
        nodes.append({'name':name,'mesh':0,'translation':xyz,'extras':{'test_only':'NOT_ANATOMY'}})
    pb=struct.pack('<'+'f'*len(pos),*pos);ib=struct.pack('<'+'I'*len(ind),*ind);raw=pb+ib
    data={'asset':{'version':'2.0','generator':'TEST_ONLY_NOT_ANATOMY — never specimen data'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(pb)},{'buffer':0,'byteOffset':len(pb),'byteLength':len(ib)}],'accessors':[{'bufferView':0,'componentType':5126,'count':len(pos)//3,'type':'VEC3'},{'bufferView':1,'componentType':5125,'count':len(ind),'type':'SCALAR'}],'buffers':[{'byteLength':len(raw)}]}
    js=json.dumps(data,separators=(',',':')).encode();js+=b' '*(-len(js)%4)
    return struct.pack('<III',0x46546c67,2,28+len(js)+len(raw))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(raw),0x004e4942)+raw
