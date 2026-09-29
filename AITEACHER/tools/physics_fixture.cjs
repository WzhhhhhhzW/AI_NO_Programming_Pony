const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={window:{},console,performance};vm.createContext(ctx);
for(const file of ['three.min.js','horse_model.js','cannon.js','physics.js'])vm.runInContext(fs.readFileSync('simulator/assets/'+file,'utf8'),ctx);
const T=ctx.THREE,horse=new T.Group(),joints={};
for(const part of ctx.window.HORSE_MODEL.parts){if(!part.joint)continue;
 const points=new Float32Array(Uint8Array.from(Buffer.from(part.positions,'base64')).buffer),tr=part.transform;
 const matrix=new T.Matrix4().set(tr[0],tr[3],tr[6],tr[9],tr[1],tr[4],tr[7],tr[10],tr[2],tr[5],tr[8],tr[11]-46.32,0,0,0,1);
 const pivot=new T.Vector3(...part.pivot).applyMatrix4(matrix);if(part.joint==='Tail')pivot.set(45,-26,0);
 for(let i=0;i<points.length;i+=3){const v=new T.Vector3(points[i],points[i+1],points[i+2]).applyMatrix4(matrix).sub(pivot);points[i]=v.x;points[i+1]=v.y;points[i+2]=v.z;}
 joints[part.joint]={points,pivot,group:new T.Group()};
}

module.exports={ctx,horse,joints};
