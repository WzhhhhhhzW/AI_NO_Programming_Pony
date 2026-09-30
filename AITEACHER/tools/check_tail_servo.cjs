const assert=require('assert');const {ctx,horse,joints}=require('./physics_fixture.cjs');
const sim=ctx.window.createHorsePhysics(horse,joints);
const target=Object.fromEntries(Object.keys(joints).map(k=>[k,0]));
const powered=Object.fromEntries(Object.keys(joints).map(k=>[k,k!=='Tail']));
function advance(seconds){for(let i=0;i<seconds*60;i++)sim.step(1/60,target,powered);return sim.info().angles.Tail;}
assert(Math.abs(advance(10))<1,'tail must hold assembly zero without valid startup PWM');
powered.Tail=true;target.Tail=45;assert(Math.abs(advance(2)-45)<1,'valid positive command must move tail');
powered.Tail=false;target.Tail=0;assert(Math.abs(advance(10)-45)<1,'missing/invalid output must hold last target, not sag or return to zero');
powered.Tail=true;target.Tail=-45;assert(Math.abs(advance(2)+45)<1,'valid negative command must move tail');
powered.Tail=false;assert(Math.abs(advance(10)+45)<1,'hold must work in either direction');
sim.reset();assert(Math.abs(advance(5))<1,'reset must restore assembly zero hold');
console.log('PASS: startup zero hold, both control directions, 10-second no-signal holding and reset.');
