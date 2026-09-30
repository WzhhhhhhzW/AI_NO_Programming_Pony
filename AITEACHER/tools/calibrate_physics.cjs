const fs=require('fs');const {ctx,horse,joints}=require('./physics_fixture.cjs');
const traces=JSON.parse(fs.readFileSync('build/turn_traces.json','utf8'));
const sim=ctx.window.createHorsePhysics(horse,joints);
function run(settings,name){sim.reset(settings);const data=traces[name];let cursor=0,maxTilt=0,heading=0,prev=0;const sign={R_Front:-1,L_Front:1,R_Rear:-1,L_Rear:1,Tail:1};
 for(let t=0;t<=data.duration;t+=1000/60){while(cursor+1<data.frames.length&&data.frames[cursor+1].t<=t)cursor++;const frame=data.frames[cursor],targets={},powered={};
 for(const id of Object.keys(sign)){const out=frame.duty[id];powered[id]=!!out&&out.pulse_ms>=.5&&out.pulse_ms<=2.5;targets[id]=powered[id]?(out.pulse_ms-1.4)*90*sign[id]:0;}
 sim.step(1/60,targets,powered);const up=new ctx.THREE.Vector3(0,1,0).applyQuaternion(horse.quaternion);const tilt=Math.acos(Math.max(-1,Math.min(1,up.y)))*180/Math.PI;maxTilt=Math.max(maxTilt,tilt);
 const forward=new ctx.THREE.Vector3(-1,0,0).applyQuaternion(horse.quaternion);const yaw=Math.atan2(forward.z,-forward.x);let delta=yaw-prev;while(delta>Math.PI)delta-=2*Math.PI;while(delta< -Math.PI)delta+=2*Math.PI;heading+=delta;prev=yaw;
 if(maxTilt>65)return {pass:false,maxTilt,time:t/1000};
 }
 return {pass:true,maxTilt,heading:heading*180/Math.PI,position:sim.info().position};}
const results=[];
for(const comY of [-25,-10,8])for(const friction of [.12,.25,.4,.65])for(const servoSpeed of [120,180,270,360]){
 const settings={mass:.45,legMass:.025,friction,torque:.18,comX:-12,comY,servoSpeed};const left=run(settings,'left');const right=left.pass?run(settings,'right'):null;const mixed=right?.pass?run(settings,'mixed'):null;
 const result={settings,left,right,mixed};results.push(result);if(mixed?.pass)console.log('PASS',JSON.stringify(result));
 fs.writeFileSync('build/physics_calibration.json',JSON.stringify(results,null,2));
}
console.log('DONE',results.length,'candidates; passing',results.filter(r=>r.mixed?.pass).length);
module.exports={run};
