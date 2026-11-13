// Text and answer areas of the worksheets; every drawing comes from assets/figures.js.
"use strict";
(() => {
// Coordinates, primes and equations such as A(−2,3), A′ and x=1 read left to right inside Hebrew text.
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
    svg.innerHTML=`<path d="${d}" fill="none" stroke="#c3d8dd" stroke-width=".7"/><rect x=".5" y=".5" width="${w-1}" height="${h-1}" fill="none" stroke="#7fa9b2" stroke-width="1"/>`;
    box.replaceChildren(svg);
  }
  function snap(){
    const boxes=Array.from(document.querySelectorAll(".squares"));
    boxes.forEach(b=>{b.replaceChildren();b.style.height="";b.style.flexGrow="";});
    const heights=boxes.map(b=>b.getBoundingClientRect().height);
    boxes.forEach((b,i)=>{b.style.flexGrow="0";b.style.height=Math.max(2,Math.floor(heights[i]/row+0.01))*row+"px";});
    boxes.forEach(draw);
    if(window.drawPlanes)window.drawPlanes(); // planes grow into the room the squares leave (assets/figures.js)
  }
  window.snapSquares=snap;
  snap();
  ["beforeprint","afterprint","resize"].forEach(e=>window.addEventListener(e,snap));
})();
