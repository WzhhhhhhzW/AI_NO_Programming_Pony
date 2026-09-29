"""从用户 3MF 中导出原始装配与网格；仅用标准库，运行时无需 CAD 软件。"""
from array import array
import base64
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import xml.etree.ElementTree as ET


def build(source, output):
    parts = []
    with ZipFile(source) as archive:
        meta = ET.fromstring(archive.read("Metadata/model_settings.config"))
        names = {o.attrib["id"]: next(m.attrib["value"] for m in o.findall("metadata") if m.get("key") == "name") for o in meta.findall("object")}
        transforms = {o.attrib["object_id"]: list(map(float, o.attrib["transform"].split())) for o in meta.findall("assemble/assemble_item")}
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        roles = {"右前腿": "R_Front", "左前腿": "L_Front", "右后腿": "R_Rear", "左后腿": "L_Rear", "尾巴": "Tail"}
        for obj in model.findall("m:resources/m:object", ns):
            oid = obj.get("id"); comp = obj.find("m:components/m:component", ns)
            path = next(v for k,v in comp.attrib.items() if k.endswith("}path"))
            root = ET.fromstring(archive.read(path.lstrip("/")))
            verts = [tuple(float(v.get(c)) for c in "xyz") for v in root.findall(".//m:vertex", ns)]
            faces = [tuple(int(f.get(c)) for c in ("v1","v2","v3")) for f in root.findall(".//m:triangle", ns)]
            # 孔的圆柱面沿 Z 轴；寻找上端小孔的包围盒中心作为转轴。
            parent = list(range(len(verts)))
            def find(i):
                while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
                return i
            for a,b,c in faces:
                u=[verts[b][k]-verts[a][k] for k in range(3)]; v=[verts[c][k]-verts[a][k] for k in range(3)]
                normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                if abs(normal[2]) < 1e-6 and abs(normal[0])+abs(normal[1]) > 1e-8:
                    parent[find(b)] = find(a); parent[find(c)] = find(a)
            groups={}
            for i in range(len(verts)): groups.setdefault(find(i),[]).append(verts[i])
            holes=[]
            for points in groups.values():
                if len(points)<10: continue
                lo=[min(p[k] for p in points) for k in range(3)]; hi=[max(p[k] for p in points) for k in range(3)]
                if 1<hi[0]-lo[0]<8 and 1<hi[1]-lo[1]<8 and hi[2]-lo[2]>2:
                    holes.append([(lo[k]+hi[k])/2 for k in range(3)])
            pivot=max(holes,key=lambda p:p[1]) if holes else [0,max(v[1] for v in verts)-15,0]
            # 0.25 mm 顶点聚类压缩，仅简化显示网格；装配坐标保持原件值。
            merged=[]; lookup={}; remap=[]
            for point in verts:
                key=tuple(round(v/.25) for v in point)
                if key not in lookup: lookup[key]=len(merged); merged.append(point)
                remap.append(lookup[key])
            indices=[]; seen=set()
            for face in faces:
                f=tuple(remap[i] for i in face)
                if len(set(f))<3 or tuple(sorted(f)) in seen: continue
                seen.add(tuple(sorted(f))); indices.extend(f)
            parts.append({"name":names[oid], "joint":roles.get(names[oid]), "transform":transforms[oid], "pivot":pivot,
                          "positions":base64.b64encode(array('f',(v for p in merged for v in p)).tobytes()).decode(),
                          "indices":base64.b64encode(array('I',indices).tobytes()).decode()})
            print(names[oid], 'vertices',len(merged),'triangles',len(indices)//3,'pivot',pivot,'holes',holes[:6])
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text("window.HORSE_MODEL="+json.dumps({"unit":"mm","source":"用户提供的 小马打印.3mf · 原始装配位置","parts":parts},ensure_ascii=False,separators=(',',':'))+";",encoding="utf-8")


if __name__ == "__main__": build(sys.argv[1],sys.argv[2])
