/* 原始 3MF 装配网格 + C 执行轨迹。动画只消费 PWM 事件，不按动作名选择预设动作。 */
(() => {
'use strict';
const names={R_Front:'右前腿',L_Front:'左前腿',R_Rear:'右后腿',L_Rear:'左后腿',Tail:'尾巴'};
const signs={R_Front:-1,L_Front:1,R_Rear:-1,L_Rear:1,Tail:1};
const $=id=>document.getElementById(id), rad=Math.PI/180;
let last=performance.now(),angles={},frame=null,manual=false,manualAngles={},mappings={},bridge=null,connected=false;
const zero={};
for(const [id,name] of Object.entries(names)){
  angles[id]=0;manualAngles[id]=0;zero[id]=1.4;
  $('joints').insertAdjacentHTML('beforeend',`<div class="joint"><div class="jointrow"><span>${name}</span><span id="v_${id}" class="jointvalue">—</span></div><div class="track"><div id="b_${id}" class="fill"></div></div></div>`);
  $('calibration').insertAdjacentHTML('beforeend',`<label>${name} 零位 ms <input id="z_${id}" type="number" value="1.4" min="0.5" max="2.5" step="0.05"></label><label>${name} 反向 <input id="s_${id}" type="checkbox" ${signs[id]<0?'checked':''}></label><label>${name} °/ms <input id="g_${id}" type="number" value="90" min="10" max="180" step="1"></label>`);
}
let scene,camera,renderer,horse,meshJoints={},floorY=96.219,orbit={yaw:2.35,pitch:.25,distance:400},target=new THREE.Vector3(0,93,0);
function error(message){$('error').style.display='block';$('error').textContent=message;window.simError=message;}
try {
  scene=new THREE.Scene();scene.fog=new THREE.Fog(0x182637,850,1800);
  camera=new THREE.PerspectiveCamera(38,1,.1,3000);
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;
  $('stage').appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xdfeaff,0x536b80,2.6));
  const light=new THREE.DirectionalLight(0xfff4e6,3.2);light.position.set(-190,330,230);light.castShadow=true;light.shadow.mapSize.set(2048,2048);
  Object.assign(light.shadow.camera,{left:-230,right:230,top:230,bottom:-230,near:1,far:850});light.shadow.bias=-.0004;scene.add(light);
  const fill=new THREE.DirectionalLight(0x87c6ff,1.3);fill.position.set(180,170,-180);scene.add(fill);
  const plane=new THREE.Mesh(new THREE.PlaneGeometry(2000,2000),new THREE.MeshStandardMaterial({color:0x263a4b,roughness:.95}));plane.rotation.x=-Math.PI/2;plane.receiveShadow=true;scene.add(plane);
  const grid=new THREE.GridHelper(1200,60,0x4c657a,0x354b5f);grid.position.y=.05;scene.add(grid);
  const ring=new THREE.Mesh(new THREE.RingGeometry(140,141.2,100),new THREE.MeshBasicMaterial({color:0x65c8b4,side:THREE.DoubleSide,transparent:true,opacity:.4}));ring.rotation.x=-Math.PI/2;ring.position.y=.1;scene.add(ring);
  window.setTheme=theme=>{
    const light=theme==='light';document.body.classList.toggle('light',light);
    scene.fog.color.setHex(light?0xdbe6f0:0x182637);
    plane.material.color.setHex(light?0xcbd7e0:0x263a4b);
    // GridHelper uses vertex colors; tint a neutral grid for each theme.
    grid.material.vertexColors=false;grid.material.color.setHex(light?0x91a9bc:0x354b5f);
    grid.material.needsUpdate=true;
    ring.material.color.setHex(light?0x258977:0x65c8b4);
  };
  horse=new THREE.Group();scene.add(horse);
  function decode64(text,Type){const bytes=Uint8Array.from(atob(text),c=>c.charCodeAt(0));return new Type(bytes.buffer);}
  for(const part of window.HORSE_MODEL.parts){
    const geometry=new THREE.BufferGeometry();const points=decode64(part.positions,Float32Array);
    geometry.setAttribute('position',new THREE.BufferAttribute(points,3));geometry.setIndex(new THREE.BufferAttribute(decode64(part.indices,Uint32Array),1));geometry.computeVertexNormals();
    const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0xf0ede5,roughness:.56,metalness:.015}));mesh.castShadow=true;mesh.receiveShadow=true;
    const tr=part.transform;const matrix=new THREE.Matrix4().set(tr[0],tr[3],tr[6],tr[9],tr[1],tr[4],tr[7],tr[10],tr[2],tr[5],tr[8],tr[11]-46.32,0,0,0,1);
    geometry.applyMatrix4(matrix);
    if(part.joint){
      const pivot=new THREE.Vector3(...part.pivot).applyMatrix4(matrix);
      // 尾巴安装面为斜置卡口，转轴中心取其与机身连接处；可用实机进一步校准。
      if(part.joint==='Tail')pivot.set(45,-26,0);
      geometry.translate(-pivot.x,-pivot.y,-pivot.z);
      const group=new THREE.Group();group.position.copy(pivot);group.add(mesh);horse.add(group);
      meshJoints[part.joint]={group,pivot,points:geometry.attributes.position.array};
      const servo=new THREE.Mesh(new THREE.BoxGeometry(22,12,15),new THREE.MeshStandardMaterial({color:0x164b92,metalness:.15,roughness:.4}));
      servo.position.copy(pivot);servo.position.z+=pivot.z>0?-10:10;if(part.joint!=='Tail')horse.add(servo);
    }else horse.add(mesh);
  }
  const oledTexture=new THREE.CanvasTexture($('oled'));oledTexture.magFilter=THREE.NearestFilter;oledTexture.minFilter=THREE.NearestFilter;
  const board=new THREE.Mesh(new THREE.BoxGeometry(2,39,25),new THREE.MeshStandardMaterial({color:0x101720,roughness:.4}));board.position.set(-59,-3,0);horse.add(board);
  const screen=new THREE.Mesh(new THREE.PlaneGeometry(32,16),new THREE.MeshBasicMaterial({map:oledTexture,side:THREE.DoubleSide}));screen.position.set(-60.2,-3,0);screen.rotation.set(0,-Math.PI/2,-Math.PI/2);horse.add(screen);
  const ctx=$('oled').getContext('2d');let lastOLED='';
  function display(frame){
    const data=frame.oled||[];const key=data.join(',')+frame.oled_on+frame.inverse+frame.flip_x+frame.flip_y;
    if(key===lastOLED)return;lastOLED=key;
    const pixels=ctx.createImageData(128,64);
    for(let y=0;y<64;y++)for(let x=0;x<128;x++){
      const sx=frame.flip_x?127-x:x,sy=frame.flip_y?63-y:y;let on=(data[(sy>>3)*128+sx]>>(sy&7))&1;if(frame.inverse)on=1-on;if(frame.oled_on===false)on=0;
      const k=(y*128+x)*4;pixels.data[k]=on?71:2;pixels.data[k+1]=on?216:10;pixels.data[k+2]=on?250:17;pixels.data[k+3]=255;
    }ctx.putImageData(pixels,0,0);oledTexture.needsUpdate=true;
    const portrait=$('oledPortrait').getContext('2d');portrait.setTransform(0,1,-1,0,64,0);portrait.drawImage($('oled'),0,0);portrait.resetTransform();
  }
  const resize=()=>{const w=$('stage').clientWidth,h=$('stage').clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();};new ResizeObserver(resize).observe($('stage'));resize();
  function cameraUpdate(){camera.position.set(target.x+Math.cos(orbit.yaw)*Math.cos(orbit.pitch)*orbit.distance,target.y+Math.sin(orbit.pitch)*orbit.distance,target.z+Math.sin(orbit.yaw)*Math.cos(orbit.pitch)*orbit.distance);camera.lookAt(target);}
  let down=null;renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];renderer.domElement.setPointerCapture(e.pointerId);});
  renderer.domElement.addEventListener('pointermove',e=>{if(!down)return;orbit.yaw-=(e.clientX-down[0])*.008;orbit.pitch=Math.max(-.05,Math.min(1.35,orbit.pitch+(e.clientY-down[1])*.006));down=[e.clientX,e.clientY];});
  renderer.domElement.addEventListener('pointerup',()=>down=null);
  renderer.domElement.addEventListener('wheel',e=>{e.preventDefault();orbit.distance=Math.max(180,Math.min(900,orbit.distance*Math.exp(e.deltaY*.001)));},{passive:false});
  $('camera').onclick=()=>{orbit={yaw:2.35,pitch:.25,distance:400};target.set(0,93,0);};

  const physics=createHorsePhysics(horse,meshJoints);
  for(const [key,value] of Object.entries(HORSE_PHYSICS_DEFAULTS))$(key).value=value;
  $('inspector').prepend($('angleTool'));
  function number(id,lo,hi,fallback){const value=Number($(id).value);return Number.isFinite(value)?Math.max(lo,Math.min(hi,value)):fallback;}
  function gain(id){return number('g_'+id,10,180,90);}
  function base(id){return number('z_'+id,.5,2.5,1.4);}
  function direction(id){return $('s_'+id).checked?-1:1;}
  function angleFor(id,pulse){return (pulse-base(id))*gain(id)*direction(id);}
  function closest(id,angle){const values=(mappings[id]?.samples||[]).filter(s=>Math.abs(angleFor(id,s.pulse_ms))<=115);return values.reduce((best,s)=>!best||Math.abs(angleFor(id,s.pulse_ms)-angle)<Math.abs(angleFor(id,best.pulse_ms)-angle)?s:best,null);}
  function manualReadout(id){
    const value=manualAngles[id],sample=closest(id,value),out=$('out_'+id);
    $('a_'+id).value=value;$('n_'+id).value=value;
    if(sample){const actual=angleFor(id,sample.pulse_ms);out.textContent=`${id}_SetDuty(${sample.value});`;$('detail_'+id).textContent=`目标 ${value.toFixed(1)}° → 整数可达 ${actual.toFixed(1)}° · ${sample.pulse_ms.toFixed(2)} ms`;}
    else{out.textContent='当前工程没有可用整数映射';$('detail_'+id).textContent=mappings[id]?.error||'等待代码载入';}
  }
  for(const [id,name] of Object.entries(names)){
    $('manualJoints').insertAdjacentHTML('beforeend',`<div class="angleRow"><label>${name} <input id="n_${id}" type="number" min="-115" max="115" step="1" value="0"> °</label><input id="a_${id}" type="range" min="-115" max="115" step="1" value="0"><output id="out_${id}"></output><small id="detail_${id}"></small></div>`);
    for(const prefix of ['a_','n_'])$(prefix+id).oninput=()=>{manualAngles[id]=number(prefix+id,-115,115,0);manualReadout(id);};
    for(const prefix of ['z_','s_','g_'])$(prefix+id).onchange=()=>{saveCalibration();manualReadout(id);};
    manualReadout(id);
  }
  function saveCalibration(){try{localStorage.setItem('horse-servo-calibration',JSON.stringify(Object.fromEntries(Object.keys(names).map(id=>[id,{zero:base(id),gain:gain(id),reverse:$('s_'+id).checked}]))));}catch(e){}}
  try{const saved=JSON.parse(localStorage.getItem('horse-servo-calibration')||'{}');for(const id of Object.keys(names))if(saved[id]){$('z_'+id).value=saved[id].zero;$('g_'+id).value=saved[id].gain;$('s_'+id).checked=saved[id].reverse;}}catch(e){}
  function sendCommand(button,payload){
    window.openAngleTool(false);
    if(bridge)bridge.action(payload);
    document.querySelectorAll('.send-command').forEach(item=>item.classList.toggle('active',item===button));
  }
  const customStorage='horse-custom-remote-v1';
  function loadCustomButtons(){
    try{
      const data=JSON.parse(localStorage.getItem(customStorage)||'[]');
      return Array.isArray(data)?data.filter(item=>item&&typeof item.label==='string'&&typeof item.payload==='string').slice(0,12):[];
    }catch(e){return [];}
  }
  let customButtons=loadCustomButtons();
  function saveCustomButtons(){try{localStorage.setItem(customStorage,JSON.stringify(customButtons));}catch(e){}}
  function renderCustomButtons(){
    const host=$('customRemote');host.replaceChildren();
    if(!customButtons.length){const empty=document.createElement('div');empty.className='custom-empty';empty.textContent='还没有自定义按钮，可按自己的蓝牙协议添加。';host.appendChild(empty);return;}
    for(const item of customButtons){
      const wrap=document.createElement('div');wrap.className='custom-action';
      const button=document.createElement('button');button.className='send-command';button.disabled=!connected;button.title='发送：'+item.payload;
      const label=document.createElement('span');label.textContent=item.label;
      const payload=document.createElement('small');payload.className='payload';payload.textContent='发送 '+item.payload;
      button.append(label,payload);button.onclick=()=>sendCommand(button,item.payload);
      const remove=document.createElement('button');remove.className='delete-custom';remove.textContent='×';remove.title='删除 '+item.label;
      remove.onclick=event=>{event.stopPropagation();customButtons=customButtons.filter(saved=>saved.id!==item.id);saveCustomButtons();renderCustomButtons();};
      wrap.append(button,remove);host.appendChild(wrap);
    }
  }
  function toggleCustomEditor(show){
    $('customEditor').classList.toggle('open',show);$('customError').textContent='';
    if(show){$('customLabel').focus();}else{$('customLabel').value='';$('customPayload').value='';}
  }
  $('showCustom').onclick=()=>toggleCustomEditor(!$('customEditor').classList.contains('open'));
  $('cancelCustom').onclick=()=>toggleCustomEditor(false);
  $('saveCustom').onclick=()=>{
    const label=$('customLabel').value.trim(),payload=$('customPayload').value.trim();
    let message='';
    if(!label)message='请填写按钮名称。';
    else if(!payload)message='请填写要发送的内容。';
    else if(!/^[\x20-\x7E]+$/.test(payload))message='发送内容请使用数字、英文字母或英文符号。';
    else if(customButtons.length>=12)message='最多可以添加 12 个自定义按钮。';
    if(message){$('customError').textContent=message;return;}
    customButtons.push({id:String(Date.now())+'_'+Math.random().toString(16).slice(2),label:label.slice(0,10),payload:payload.slice(0,32)});
    saveCustomButtons();renderCustomButtons();toggleCustomEditor(false);
  };
  $('customPayload').addEventListener('keydown',event=>{if(event.key==='Enter')$('saveCustom').click();});
  renderCustomButtons();
  window.setCommands=commands=>{
    $('remote').replaceChildren();
    for(const {char,label} of commands){const button=document.createElement('button');button.className='send-command';button.textContent=label;button.title='串口字符：'+char;button.id='action_'+char;button.disabled=!connected;button.onclick=()=>sendCommand(button,char);$('remote').appendChild(button);}
    if(!commands.length){const note=document.createElement('span');note.className='muted';note.textContent='未识别到可用的串口动作分支';$('remote').appendChild(note);}
  };
  new QWebChannel(qt.webChannelTransport,channel=>{bridge=channel.objects.controller;connected=true;document.querySelectorAll('.send-command').forEach(button=>button.disabled=false);});
  window.openAngleTool=function(enabled){manual=!!enabled;document.body.classList.toggle('manual',manual);if(manual){target.set(0,93,0);orbit.distance=440;}$('angleTool').style.display=manual?'block':'none';if(manual){for(const id of Object.keys(names)){manualAngles[id]=THREE.MathUtils.clamp(Math.round(angles[id]||0),-115,115);manualReadout(id);}}if(bridge)bridge.manual(manual);};
  $('angles').onclick=()=>window.openAngleTool(!manual);$('closeAngles').onclick=()=>window.openAngleTool(false);
  $('copyPose').onclick=()=>{const rows=[];for(const id of Object.keys(names)){const sample=closest(id,manualAngles[id]);if(!sample){$('copyStatus').textContent='存在不可计算的关节，请先检查代码和映射。';return;}rows.push(`${id}_SetDuty(${sample.value});`);}if(bridge){bridge.copyCode(rows.join('\n'));$('copyStatus').textContent='已复制五路整数控制代码。';}};
  $('resetCal').onclick=()=>{for(const id of Object.keys(names)){$('z_'+id).value=1.4;$('s_'+id).checked=signs[id]<0;$('g_'+id).value=90;manualReadout(id);}saveCalibration();};
  function resetPhysics(){physics.reset({mass:number('mass',.05,3,.45),legMass:number('legMass',.005,.2,.025),friction:number('friction',0,2,HORSE_PHYSICS_DEFAULTS.friction),torque:number('torque',.01,2,.18),comX:number('comX',-50,50,-12),comY:number('comY',-25,80,HORSE_PHYSICS_DEFAULTS.comY),servoSpeed:number('servoSpeed',30,600,HORSE_PHYSICS_DEFAULTS.servoSpeed),tailServoSpeed:number('tailServoSpeed',30,1200,HORSE_PHYSICS_DEFAULTS.tailServoSpeed)});}
  $('physicsReset').onclick=resetPhysics;
  $('physicsDefaults').onclick=()=>{for(const [key,value] of Object.entries(HORSE_PHYSICS_DEFAULTS))$(key).value=value;resetPhysics();};
  window.setMappings=data=>{mappings=data;for(const id of Object.keys(names))manualReadout(id);};
  window.setLiveFrame=data=>{frame=data;$('connection').textContent=data.receiving?'● 已连接 · 等待指令':'● 已连接 · 执行动作 / 初始化';document.querySelectorAll('.send-command').forEach(b=>b.disabled=!connected);};
  window.liveError=message=>{error(message);$('connection').textContent='代码执行停止';document.querySelectorAll('.send-command').forEach(b=>b.disabled=true);};
  window.resetLive=()=>{$('remote').replaceChildren();window.openAngleTool(false);frame=null;mappings={};angles=Object.fromEntries(Object.keys(names).map(k=>[k,0]));resetPhysics();$('error').style.display='none';$('connection').textContent='正在载入代码…';$('copyStatus').textContent='';document.querySelectorAll('.send-command').forEach(b=>b.disabled=true);};
  function manualPose(){let minY=0;horse.quaternion.identity();horse.position.set(0,0,0);
    for(const [id,j] of Object.entries(meshJoints)){j.group.position.copy(j.pivot);j.group.rotation.set(id==='Tail'?manualAngles[id]*rad:0,0,id!=='Tail'?manualAngles[id]*rad:0);if(id!=='Tail'){const c=Math.cos(manualAngles[id]*rad),s=Math.sin(manualAngles[id]*rad),p=j.points;for(let i=0;i<p.length;i+=3)minY=Math.min(minY,p[i]*s+p[i+1]*c+j.pivot.y);}}
    horse.position.y=Math.max(53,-minY);
  }
  function animate(now){requestAnimationFrame(animate);const dt=Math.min(.05,(now-last)/1000);last=now;
    const targets={},powered={};
    for(const id of Object.keys(names)){const output=frame?.duty[id];powered[id]=!!output&&output.pulse_ms>=.5&&output.pulse_ms<=2.5;targets[id]=powered[id]?THREE.MathUtils.clamp(angleFor(id,output.pulse_ms),-115,115):0;}
    if(manual)manualPose();else physics.step(dt,targets,powered);
    const state=physics.info();angles=manual?{...manualAngles}:state.angles;
    for(const id of Object.keys(names)){const output=frame?.duty[id];$('v_'+id).textContent=manual?`${angles[id].toFixed(0)}° · 手动`:output?`${output.percent.toFixed(1)}% · ${powered[id]?angles[id].toFixed(0)+'°':id==='Tail'?'超范围 · 保持 '+angles[id].toFixed(0)+'°':'超范围'}`:id==='Tail'?'保持 '+angles[id].toFixed(0)+'°':'未输出';$('v_'+id).style.color=output&&!powered[id]?'var(--joint-warning)':'var(--joint-good)';$('b_'+id).style.width=(angles[id]+115)/230*100+'%';}
    if(frame){display(frame);$('time').textContent=(frame.t/1000).toFixed(2)+'s';$('source').textContent=manual?'角度测算 · 代码和物理已暂停':frame.source||'实时执行 / 等待输入';}
    $('physicsState').textContent=`${state.tilt>65?'已侧翻 · ':''}接触点 ${state.contacts} · X ${(state.position[0]*100).toFixed(1)} cm · Z ${(state.position[2]*100).toFixed(1)} cm · 航向 ${(state.rotation[1]/rad).toFixed(1)}° · 俯仰 ${(state.rotation[2]/rad).toFixed(1)}° · 横滚 ${(state.rotation[0]/rad).toFixed(1)}°`;
    if(!manual){target.x=horse.position.x;target.z=horse.position.z;}
    cameraUpdate();renderer.render(scene,camera);window.simReady=true;
  }requestAnimationFrame(animate);
  window.simDebug=()=>({ready:window.simReady,manual,time:frame?.t||0,angles:{...angles},parts:HORSE_MODEL.parts.length,physics:physics.info(),mappings,receiving:frame?.receiving});
}catch(e){error('3D 初始化失败：'+e.message+'。请检查显卡驱动和安装包资源。');}
})();
