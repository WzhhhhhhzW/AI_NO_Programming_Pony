const fs=require('fs'),assert=require('assert'),{execFileSync}=require('child_process'),path=require('path');
execFileSync(path.resolve('.venv/Scripts/python.exe'),['tools/export_simulation_turns.py'],{stdio:'inherit'});const {ctx,horse,joints}=require('./physics_fixture.cjs');
const traces=JSON.parse(fs.readFileSync('build/turn_traces_long.json','utf8'));
const sim=ctx.window.createHorsePhysics(horse,joints);
function run(settings,name,dt=1/60,stretch=1){sim.reset(settings);const data=traces[name];let cursor=0,maxTilt=0,heading=0,prev=0;const sign={R_Front:-1,L_Front:1,R_Rear:-1,L_Rear:1,Tail:1};
 for(let t=0;t<=data.duration;t+=dt*1000/stretch){while(cursor+1<data.frames.length&&data.frames[cursor+1].t<=t)cursor++;const frame=data.frames[cursor],targets={},powered={};
 for(const id of Object.keys(sign)){const out=frame.duty[id];powered[id]=!!out&&out.pulse_ms>=.5&&out.pulse_ms<=2.5;targets[id]=powered[id]?(out.pulse_ms-1.4)*90*sign[id]:0;}
 sim.step(dt,targets,powered);const up=new ctx.THREE.Vector3(0,1,0).applyQuaternion(horse.quaternion);const tilt=Math.acos(Math.max(-1,Math.min(1,up.y)))*180/Math.PI;maxTilt=Math.max(maxTilt,tilt);
 const forward=new ctx.THREE.Vector3(-1,0,0).applyQuaternion(horse.quaternion);const yaw=Math.atan2(forward.z,-forward.x);let delta=yaw-prev;while(delta>Math.PI)delta-=2*Math.PI;while(delta< -Math.PI)delta+=2*Math.PI;heading+=delta;prev=yaw;
 if(maxTilt>40)return {pass:false,maxTilt,time:t/1000};
 }
 return {pass:true,maxTilt,heading:heading*180/Math.PI,position:sim.info().position};}
const results=[];
const defaults={...ctx.window.HORSE_PHYSICS_DEFAULTS};
const old=run({...defaults,comY:8,friction:.65,servoSpeed:360},'left');
assert(!old.pass,'old defaults must reproduce the unstable reference turn');
for(const dt of [1/30,1/60])for(const stretch of [1,1.2])for(const name of ['left','right','mixed']){
 const result=run(defaults,name,dt,stretch);assert(result.pass,name+' tilted '+result.maxTilt);assert(result.maxTilt<35,'excess tilt');
 if(name==='left')assert(result.heading>5,'left turn direction');if(name==='right')assert(result.heading< -5,'right turn direction');
 results.push({fps:Math.round(1/dt),stretch,name,...result});
}
fs.writeFileSync('build/turn_stability_report.json',JSON.stringify({defaults,old,results},null,2));
console.log('PASS: previous fall reproduced; six left, six right and six alternating turns stay upright at 30/60 FPS and 20% timing stretch.');
console.log('Worst tilt:',Math.max(...results.map(r=>r.maxTilt)).toFixed(2),'degrees');
