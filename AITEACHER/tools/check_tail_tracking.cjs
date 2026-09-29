const assert=require('assert');const {ctx,horse,joints}=require('./physics_fixture.cjs');
const sim=ctx.window.createHorsePhysics(horse,joints),power=Object.fromEntries(Object.keys(joints).map(k=>[k,true])),target=Object.fromEntries(Object.keys(joints).map(k=>[k,0]));
for(const fps of [30,60,120]){
 sim.reset();target.Tail=0;for(let i=0;i<fps;i++)sim.step(1/fps,target,power);
 for(const goal of [-72,72,-72,72,0]){
  target.Tail=goal;let time=0;while(time<.35-1e-9){const dt=Math.min(1/fps,.35-time);sim.step(dt,target,power);time+=dt;}
  assert(Math.abs(sim.info().angles.Tail-goal)<2,`${fps} FPS: ${goal} -> ${sim.info().angles.Tail}`);
 }
 power.Tail=false;for(let i=0;i<fps;i++)sim.step(1/fps,target,power);
 assert(Math.abs(sim.info().angles.Tail)<2,'tail must keep servo hold');power.Tail=true;
}
console.log('PASS: tail reaches ±72 degrees and zero within 350ms at 30/60/120 FPS; unpowered hold retained');
