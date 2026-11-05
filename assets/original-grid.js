"use strict";
(() => {
const ns="http://www.w3.org/2000/svg";
const add=(p,tag,a,text)=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(a))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=String(text);p.appendChild(el);return el;};
// negative numbers carry a true minus sign and the drawings read left to right, so −6 never prints as "6-" on an RTL page
const minus=n=>n<0?"−"+(-n):String(n);
for(const svg of document.querySelectorAll("svg[data-shape]:not([data-plane])")){svg.style.direction="ltr";
const vertices=(svg.dataset.shape||"").split(";").map(s=>s.split(",").map(Number));if(vertices.some(p=>p.length!==2||p.some(x=>!Number.isFinite(x))))continue;
const labels=(svg.dataset.labels||"A,B,C").split(",");const unit=16,ox=125,oy=125,pos=p=>[ox+p[0]*unit,oy-p[1]*unit];
svg.setAttribute("viewBox","0 0 250 250");svg.setAttribute("role","img");svg.setAttribute("aria-label",svg.dataset.caption||"מצולע במערכת צירים");
add(svg,"rect",{x:1,y:1,width:248,height:248,fill:"#fff"});
for(let n=-7;n<=7;n++){let u=ox+n*unit;add(svg,"line",{x1:u,y1:8,x2:u,y2:242,stroke:n===0?"#406273":"#e2eded","stroke-width":n===0?1.8:0.8});add(svg,"line",{x1:8,y1:u,x2:242,y2:u,stroke:n===0?"#406273":"#e2eded","stroke-width":n===0?1.8:0.8});if(n!==0&&n%2===0){add(svg,"text",{x:u,y:135,"text-anchor":"middle","font-size":10,fill:"#506b7a"},minus(n));add(svg,"text",{x:116,y:u+3,"text-anchor":"end","font-size":10,fill:"#506b7a"},minus(-n))}}
add(svg,"text",{x:238,y:118,"font-size":13,fill:"#294d5e"},"x");add(svg,"text",{x:130,y:14,"font-size":13,fill:"#294d5e"},"y");
const kx=Number(svg.dataset.mirrorX),ky=Number(svg.dataset.mirrorY);
if(svg.dataset.mirrorX!==undefined){const u=ox+kx*unit;add(svg,"line",{x1:u,y1:4,x2:u,y2:246,stroke:"#9b4b94","stroke-width":1.6,"stroke-dasharray":"5 4"})}
if(svg.dataset.mirrorY!==undefined){const u=oy-ky*unit;add(svg,"line",{x1:4,y1:u,x2:246,y2:u,stroke:"#9b4b94","stroke-width":1.6,"stroke-dasharray":"5 4"})}
add(svg,"polygon",{points:vertices.map(p=>pos(p).join(",")).join(" "),fill:"#b9e7dc","fill-opacity":".75",stroke:"#07766d","stroke-width":2.2});
vertices.forEach((p,i)=>{const [x,y]=pos(p);add(svg,"circle",{cx:x,cy:y,r:3.5,fill:"#036b68",stroke:"#fff","stroke-width":1});add(svg,"text",{x:x+6,y:y-7,"font-size":12,"font-weight":"bold",fill:"#005954"},labels[i]||"")});
if(svg.dataset.center){
  const center=svg.dataset.center.split(",").map(Number);
  if(center.length===2&&center.every(Number.isFinite)){
    const [x,y]=pos(center);
    add(svg,"circle",{cx:x,cy:y,r:5.2,fill:"#a341a3",stroke:"#fff","stroke-width":1.4});
    add(svg,"text",{x:x+9,y:y-9,"font-size":13,"font-weight":"bold",fill:"#8e318e"},svg.dataset.centerLabel||"P");
  }
}

}
const pattern=/(?:[A-Z][′″']?)?\((?:[−-]?\d+|[xy]),\s*(?:[−-]?\d+|[xy])\)|\b[xy]\s*=\s*[−-]?\d+|(?:[A-Z][′″'])+/g;
const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
const nodes=[];
while(walker.nextNode()){
  const n=walker.currentNode,p=n.parentElement;
  if(!p||p.closest("svg,script,style,bdi,.ltr")||!pattern.test(n.textContent))continue;
  pattern.lastIndex=0;nodes.push(n);
}
for(const node of nodes){
  const raw=node.textContent,fragment=document.createDocumentFragment();let start=0;
  pattern.lastIndex=0;
  for(const m of raw.matchAll(pattern)){
    if(m.index>start)fragment.appendChild(document.createTextNode(raw.slice(start,m.index)));
    const token=document.createElement("bdi");token.dir="ltr";token.className="ltr";token.textContent=m[0];fragment.appendChild(token);
    start=m.index+m[0].length;
  }
  if(start<raw.length)fragment.appendChild(document.createTextNode(raw.slice(start)));
  node.replaceWith(fragment);
}
})();
// Precise coordinate planes on the two-page sheets: drawn at true printed size (one unit = data-unit mm), every unit
// gridded and numbered. A plane in a stretching frame fills the frame's height with whole units.
(function(){
  const NS="http://www.w3.org/2000/svg", mm=96/25.4;
  const add=(p,tag,a,text)=>{const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(a))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=String(text);p.appendChild(el);return el;};
  const minus=n=>n<0?"−"+(-n):String(n), pair=s=>s.split(",").map(Number), f=v=>+v.toFixed(2);
  function draw(svg,rows){
    const [x0,x1]=pair(svg.dataset.x),[b0,b1]=pair(svg.dataset.y),u=Number(svg.dataset.unit||6.5);
    const extra=Math.max(0,rows-(b1-b0)),y1=b1+Math.floor(extra/2),y0=b0-Math.ceil(extra/2);
    // room for the arrows and axis names above and to the right; a narrow edge below and to the left
    const top=0.95*u,right=0.95*u,bottom=(y0<0?0.45:0.95)*u,left=(x0<0?0.45:0.95)*u;
    const W=f((x1-x0)*u+left+right),H=f((y1-y0)*u+top+bottom),X=x=>f(left+(x-x0)*u),Y=y=>f(top+(y1-y)*u);
    const small=Math.min(3.2,Math.max(2.3,0.36*u)),big=Math.min(4.6,Math.max(3.4,0.52*u)),halo={stroke:"#fff","stroke-width":0.7,"paint-order":"stroke"};
    svg.replaceChildren();
    svg.setAttribute("viewBox",`0 0 ${W} ${H}`);svg.setAttribute("width",W+"mm");svg.setAttribute("height",H+"mm");
    svg.setAttribute("role","img");svg.setAttribute("aria-label",svg.dataset.caption||"מערכת צירים");
    svg.setAttribute("font-family","Arial,'Noto Sans Hebrew',sans-serif");svg.style.direction="ltr";
    add(svg,"rect",{x:0.3,y:0.3,width:f(W-0.6),height:f(H-0.6),rx:2,fill:"#fff",stroke:"#b6cdd2","stroke-width":0.3});
    let d="";
    for(let x=x0;x<=x1;x++)d+=`M${X(x)} ${Y(y1)}V${Y(y0)}`;
    for(let y=y0;y<=y1;y++)d+=`M${X(x0)} ${Y(y)}H${X(x1)}`;
    add(svg,"path",{d,fill:"none",stroke:"#c3d9dd","stroke-width":0.22});
    const ink="#22414d",ax=Y(0),ay=X(0),tip=f(0.75*u);
    add(svg,"path",{d:`M${X(x0)} ${ax}H${f(X(x1)+tip-1)}M${ay} ${Y(y0)}V${f(Y(y1)-tip+1)}`,fill:"none",stroke:ink,"stroke-width":0.45});
    add(svg,"path",{d:`M${f(X(x1)+tip)} ${ax}l-2.2 -1v2zM${ay} ${f(Y(y1)-tip)}l-1 2.2h2z`,fill:ink});
    add(svg,"text",{x:f(X(x1)+tip-0.6),y:f(ax-1.8),"font-size":big,"font-style":"italic","text-anchor":"end",fill:ink,...halo},"x");
    add(svg,"text",{x:f(ay+1.6),y:f(Y(y1)-tip+2.6),"font-size":big,"font-style":"italic",fill:ink,...halo},"y");
    for(let x=x0;x<=x1;x++)if(x)add(svg,"text",{x:X(x),y:f(ax+small+0.9),"font-size":small,"text-anchor":"middle",fill:"#3f5d69",...halo},minus(x));
    for(let y=y0;y<=y1;y++)if(y)add(svg,"text",{x:f(ay-0.9),y:f(Y(y)+small*0.36),"font-size":small,"text-anchor":"end",fill:"#3f5d69",...halo},minus(y));
    add(svg,"text",{x:f(ay-0.9),y:f(ax+small+0.9),"font-size":small,"text-anchor":"end",fill:"#3f5d69",...halo},"0");
    if(svg.dataset.mirrorX!==undefined){
      const k=Number(svg.dataset.mirrorX),line=X(k);
      add(svg,"path",{d:`M${line} ${Y(y1)}V${Y(y0)}`,fill:"none",stroke:"#9b4b94","stroke-width":0.5,"stroke-dasharray":"1.8 1.2"});
      add(svg,"text",{x:f(line+1.1),y:f(Y(y1)+big+0.6),"font-size":small+0.5,"font-weight":"bold",fill:"#8e318e",...halo},"x="+minus(k));
    }
    const pts=(svg.dataset.shape||"").split(";").filter(Boolean).map(pair);
    if(pts.length){
      const names=(svg.dataset.labels||"A,B,C").split(","),cx=pts.reduce((a,p)=>a+p[0],0)/pts.length,cy=pts.reduce((a,p)=>a+p[1],0)/pts.length;
      add(svg,"polygon",{points:pts.map(p=>X(p[0])+","+Y(p[1])).join(" "),fill:"#b9e7dc","fill-opacity":0.8,stroke:"#07766d","stroke-width":0.55,"stroke-linejoin":"round"});
      pts.forEach((p,i)=>{
        let dx=p[0]-cx,dy=p[1]-cy;const n=Math.hypot(dx,dy)||1;dx/=n;dy/=n;
        add(svg,"circle",{cx:X(p[0]),cy:Y(p[1]),r:f(Math.min(1.2,Math.max(0.8,0.13*u))),fill:"#036b68",stroke:"#fff","stroke-width":0.25});
        add(svg,"text",{x:f(X(p[0])+dx*0.5*big*1.25),y:f(Y(p[1])-dy*0.5*big*1.25+big*0.36),"font-size":big,"font-weight":"bold","text-anchor":"middle",fill:"#005954",...halo},names[i]||"");
      });
    }
    return [W,H];
  }
  const planes=Array.from(document.querySelectorAll("svg[data-plane]"));
  planes.forEach(svg=>{
    const [b0,b1]=pair(svg.dataset.y),[W,H]=draw(svg,b1-b0),frame=svg.parentElement;
    if(frame.classList.contains("plane")){frame.style.width=W+"mm";frame.style.minHeight=H+"mm";}
  });
  window.drawPlanes=()=>planes.forEach(svg=>{
    const [b0,b1]=pair(svg.dataset.y),u=Number(svg.dataset.unit||6.5),frame=svg.parentElement;
    const room=frame.classList.contains("plane")?Math.floor((frame.getBoundingClientRect().height/mm-(b0<0?1.4:1.9)*u-0.4)/u):0;
    draw(svg,Math.max(b1-b0,room));
  });
})();
// Squared answer areas: whole 5 mm squares only, drawn as a crisp vector grid. In print each box is first
// trimmed to full rows, so no row is cut at the frame. The PDF build calls window.snapSquares().
(function(){
  const row=5*96/25.4, NS="http://www.w3.org/2000/svg";
  function draw(box){
    const w=box.clientWidth, h=box.clientHeight, cols=Math.max(1,Math.round(w/row)), rows=Math.max(1,Math.round(h/row));
    let d="";
    for(let i=1;i<cols;i++){const x=(i*w/cols).toFixed(2);d+=`M${x} 0V${h}`;}
    for(let j=1;j<rows;j++){const y=(j*h/rows).toFixed(2);d+=`M0 ${y}H${w}`;}
    const svg=document.createElementNS(NS,"svg");
    svg.setAttribute("viewBox",`0 0 ${w} ${h}`);svg.setAttribute("aria-hidden","true");
    svg.innerHTML=`<path d="${d}" fill="none" stroke="#c3d8dd" stroke-width=".7"/><rect x=".5" y=".5" width="${w-1}" height="${h-1}" rx="3" fill="none" stroke="#7fa9b2" stroke-width="1"/>`;
    box.replaceChildren(svg);
  }
  function snap(){
    const boxes=Array.from(document.querySelectorAll(".squares"));
    boxes.forEach(b=>{b.replaceChildren();b.style.height="";b.style.flexGrow="";});
    const heights=boxes.map(b=>b.getBoundingClientRect().height);
    boxes.forEach((b,i)=>{b.style.flexGrow="0";b.style.height=Math.max(2,Math.floor(heights[i]/row+0.01))*row+"px";});
    boxes.forEach(draw);
    if(window.drawPlanes)window.drawPlanes();
  }
  window.snapSquares=snap;
  snap();
  ["beforeprint","afterprint","resize"].forEach(e=>window.addEventListener(e,snap));
})();
