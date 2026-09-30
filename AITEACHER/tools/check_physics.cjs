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
const physics=ctx.window.createHorsePhysics(horse,joints),zero=Object.fromEntries(Object.keys(joints).map(k=>[k,0])),power=Object.fromEntries(Object.keys(joints).map(k=>[k,true]));
function step(n,target=zero){for(let i=0;i<n;i++)physics.step(1/60,target,power);return physics.info();}
let initial=physics.info(),fallen=step(1);assert(fallen.position[1]<initial.position[1],'gravity should lower freely suspended body');
let stand=step(600);assert(stand.contacts>0);assert(stand.position.every(Number.isFinite));assert(Math.abs(stand.rotation[0])<.5&&Math.abs(stand.rotation[2])<.5,'standing must remain upright');
function trial(friction){physics.reset({friction});step(120);const start=physics.info();for(let i=0;i<10;i++){step(17,{R_Front:-54,L_Front:i%2?54:-54,R_Rear:i%2?54:-36,L_Rear:i%2?-36:54,Tail:0});}const end=physics.info();return {yaw:end.rotation[1]-start.rotation[1],dx:end.position[0]-start.position[0],dz:end.position[2]-start.position[2],roll:end.rotation[0]};}
const grippy=trial(.65),slippery=trial(0);assert(Math.abs(grippy.dx)+Math.abs(grippy.dz)>.005);assert(Math.abs(grippy.yaw)>.01);assert(Math.abs(grippy.dx-slippery.dx)+Math.abs(grippy.dz-slippery.dz)>.001,'contact friction must affect movement');
console.log(JSON.stringify({stand:stand.position,grippy,slippery}));console.log('PASS: gravity, stable standing, contact-driven turn and friction sensitivity.');
