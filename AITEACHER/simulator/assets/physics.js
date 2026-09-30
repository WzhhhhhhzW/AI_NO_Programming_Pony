/* SI 单位刚体模型。关节力矩与地面接触共同决定机身平移和倾斜。 */
window.HORSE_PHYSICS_DEFAULTS = Object.freeze({mass:.45,legMass:.025,friction:.25,torque:.18,comX:-12,comY:-15,servoSpeed:180,tailServoSpeed:600});
window.createHorsePhysics = function(horse, joints) {
  const C = window.CANNON, S = .001;
  let world, body, limbs={}, constraints=[], contacts=0, accumulator=0, peakTilt=0;
  let settings={...window.HORSE_PHYSICS_DEFAULTS};
  const vec=(p)=>new C.Vec3(p.x*S,p.y*S,p.z*S);
  const center=()=>new C.Vec3(settings.comX*S,settings.comY*S,0);
  const relative=(p,c)=>new C.Vec3(p.x-c.x,p.y-c.y,p.z-c.z);
  function reset(values={}) {
    settings={...settings,...values}; accumulator=0;peakTilt=0;
    world=new C.World({gravity:new C.Vec3(0,-9.81,0)});
    world.solver.iterations=40;world.solver.tolerance=1e-8;
    const groundMat=new C.Material(),footMat=new C.Material();
    world.addContactMaterial(new C.ContactMaterial(groundMat,footMat,{friction:settings.friction,restitution:0,contactEquationStiffness:1e7,contactEquationRelaxation:4}));
    const ground=new C.Body({mass:0,material:groundMat,collisionFilterGroup:1,collisionFilterMask:2});
    ground.addShape(new C.Plane());ground.quaternion.setFromEuler(-Math.PI/2,0,0);world.addBody(ground);
    const com=center(), height=.098;
    body=new C.Body({mass:settings.mass,position:new C.Vec3(com.x,height+com.y,com.z),material:footMat,collisionFilterGroup:2,collisionFilterMask:1,angularDamping:.12,linearDamping:.06});
    body.addShape(new C.Box(new C.Vec3(.064,.028,.036)),relative(new C.Vec3(0,-.004,0),com));
    body.addShape(new C.Box(new C.Vec3(.023,.063,.020)),relative(new C.Vec3(-.053,.080,0),com));
    world.addBody(body);limbs={};constraints=[];
    for(const [id,j] of Object.entries(joints)) {
      const p=j.points; let min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
      for(let i=0;i<p.length;i+=3)for(let k=0;k<3;k++){min[k]=Math.min(min[k],p[i+k]);max[k]=Math.max(max[k],p[i+k]);}
      const offset=new C.Vec3((min[0]+max[0])*.0005,(min[1]+max[1])*.0005,(min[2]+max[2])*.0005), pivot=vec(j.pivot);
      const limb=new C.Body({mass:id==='Tail'?.018:settings.legMass,material:footMat,position:new C.Vec3(pivot.x+offset.x,height+pivot.y+offset.y,pivot.z+offset.z),collisionFilterGroup:2,collisionFilterMask:1,angularDamping:.08});
      // 沿原始零件高度分段建立碰撞盒，避免把弯腿当成长方块。
      const sections=id==='Tail'?2:5;
      for(let b=0;b<sections;b++){
        const lo=min[1]+(max[1]-min[1])*b/sections,hi=min[1]+(max[1]-min[1])*(b+1)/sections;
        let xmin=Infinity,xmax=-Infinity,zmin=Infinity,zmax=-Infinity;
        for(let i=0;i<p.length;i+=3)if(p[i+1]>=lo&&p[i+1]<=hi){xmin=Math.min(xmin,p[i]);xmax=Math.max(xmax,p[i]);zmin=Math.min(zmin,p[i+2]);zmax=Math.max(zmax,p[i+2]);}
        if(!Number.isFinite(xmin))continue;
        const c=new C.Vec3((xmin+xmax)*.0005,(lo+hi)*.0005,(zmin+zmax)*.0005);
        limb.addShape(new C.Box(new C.Vec3(Math.max(.002,(xmax-xmin)*.0005),Math.max(.002,(hi-lo)*.0005),Math.max(.002,(zmax-zmin)*.0005))),relative(c,offset));
      }
      world.addBody(limb);
      const axis=id==='Tail'?new C.Vec3(1,0,0):new C.Vec3(0,0,1);
      const hinge=new C.HingeConstraint(body,limb,{pivotA:relative(pivot,com),pivotB:offset.negate(),axisA:axis,axisB:axis,maxForce:200,collideConnected:false});
      world.addConstraint(hinge);constraints.push(hinge);limbs[id]={body:limb,offset,axis,hinge,heldTarget:0};
    }
  }
  function angle(id){
    const l=limbs[id],q=body.quaternion.conjugate().mult(l.body.quaternion);
    let a=2*Math.atan2(id==='Tail'?q.x:q.z,q.w);while(a>Math.PI)a-=Math.PI*2;while(a< -Math.PI)a+=Math.PI*2;return a;
  }
  function step(dt,targets,powered){
    accumulator=Math.min(accumulator+dt,.1);
    while(accumulator>=1/240){
      for(const [id,l] of Object.entries(limbs)){
        const a=angle(id),limit=Math.max(-115*Math.PI/180,Math.min(115*Math.PI/180,a));
        // 尾巴按已安装、持续保持位置的舵机建模。无有效新指令时保留
        // 上次目标（上电为装配零位），仍使用有限力矩，不能释放为自由铰链。
        if(powered[id] && Number.isFinite(targets[id])) l.heldTarget=targets[id]*Math.PI/180;
        if(powered[id]||id==='Tail'||Math.abs(limit-a)>.001){
          const desired=powered[id]||id==='Tail'?l.heldTarget:limit;
          l.hinge.enableMotor();l.hinge.setMotorMaxForce(settings.torque);
          // 方程定义 A 角速度减 B 角速度，因此跟踪 B 相对 A 的转角时取负号。
          const speed=(id==='Tail'?settings.tailServoSpeed:settings.servoSpeed)*Math.PI/180;
          const gain=id==='Tail'?32:16;
          l.hinge.setMotorSpeed(-Math.max(-speed,Math.min(speed,(desired-a)*gain)));
        }else l.hinge.disableMotor();
      }
      world.step(1/240);accumulator-=1/240;
      peakTilt=Math.max(peakTilt,Math.acos(Math.max(-1,Math.min(1,body.quaternion.vmult(new C.Vec3(0,1,0)).y)))*180/Math.PI);
    }
    contacts=world.contacts.length;
    const origin=body.position.vsub(body.quaternion.vmult(center()));
    horse.position.set(origin.x/S,origin.y/S,origin.z/S);horse.quaternion.copy(body.quaternion);
    const inv=body.quaternion.conjugate();
    for(const [id,l] of Object.entries(limbs)){
      const pivot=l.body.position.vsub(l.body.quaternion.vmult(l.offset));
      const local=inv.vmult(pivot.vsub(origin));
      joints[id].group.position.set(local.x/S,local.y/S,local.z/S);
      joints[id].group.quaternion.copy(inv.mult(l.body.quaternion));
    }
  }
  function info(){const e=new C.Vec3();body.quaternion.toEuler(e,'YZX');return {engine:'cannon-es 0.20.0',contacts,peakTilt,tilt:Math.acos(Math.max(-1,Math.min(1,body.quaternion.vmult(new C.Vec3(0,1,0)).y)))*180/Math.PI,position:[body.position.x,body.position.y,body.position.z],rotation:[e.x,e.y,e.z],angles:Object.fromEntries(Object.keys(limbs).map(k=>[k,angle(k)*180/Math.PI])),settings:{...settings}};}
  reset();return {step,reset,info};
};
