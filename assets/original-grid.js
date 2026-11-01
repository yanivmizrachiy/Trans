"use strict";
(() => {
const ns="http://www.w3.org/2000/svg";
const add=(p,tag,a,text)=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(a))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=String(text);p.appendChild(el);return el;};
for(const svg of document.querySelectorAll("svg[data-shape]")){
const vertices=(svg.dataset.shape||"").split(";").map(s=>s.split(",").map(Number));if(vertices.some(p=>p.length!==2||p.some(x=>!Number.isFinite(x))))continue;
const labels=(svg.dataset.labels||"A,B,C").split(",");const unit=16,ox=125,oy=125,pos=p=>[ox+p[0]*unit,oy-p[1]*unit];
svg.setAttribute("viewBox","0 0 250 250");svg.setAttribute("role","img");svg.setAttribute("aria-label",svg.dataset.caption||"מצולע במערכת צירים");
add(svg,"rect",{x:1,y:1,width:248,height:248,fill:"#fff"});
for(let n=-7;n<=7;n++){let u=ox+n*unit;add(svg,"line",{x1:u,y1:8,x2:u,y2:242,stroke:n===0?"#406273":"#e2eded","stroke-width":n===0?1.8:0.8});add(svg,"line",{x1:8,y1:u,x2:242,y2:u,stroke:n===0?"#406273":"#e2eded","stroke-width":n===0?1.8:0.8});if(n!==0&&n%2===0){add(svg,"text",{x:u,y:135,"text-anchor":"middle","font-size":10,fill:"#506b7a"},n);add(svg,"text",{x:116,y:u+3,"text-anchor":"end","font-size":10,fill:"#506b7a"},-n)}}
add(svg,"text",{x:238,y:118,"font-size":13,fill:"#294d5e"},"x");add(svg,"text",{x:130,y:14,"font-size":13,fill:"#294d5e"},"y");
const kx=Number(svg.dataset.mirrorX),ky=Number(svg.dataset.mirrorY);
if(svg.dataset.mirrorX!==undefined){const u=ox+kx*unit;add(svg,"line",{x1:u,y1:4,x2:u,y2:246,stroke:"#9b4b94","stroke-width":1.6,"stroke-dasharray":"5 4"})}
if(svg.dataset.mirrorY!==undefined){const u=oy-ky*unit;add(svg,"line",{x1:4,y1:u,x2:246,y2:u,stroke:"#9b4b94","stroke-width":1.6,"stroke-dasharray":"5 4"})}
add(svg,"polygon",{points:vertices.map(p=>pos(p).join(",")).join(" "),fill:"#b9e7dc","fill-opacity":".75",stroke:"#07766d","stroke-width":2.2});
vertices.forEach((p,i)=>{const [x,y]=pos(p);add(svg,"circle",{cx:x,cy:y,r:3.5,fill:"#036b68",stroke:"#fff","stroke-width":1});add(svg,"text",{x:x+6,y:y-7,"font-size":12,"font-weight":"bold",fill:"#005954"},labels[i]||"")});
}}
)();