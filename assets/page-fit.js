/* Printed A4 sheets: the text stays at its book size and shrinks only if the page overflows.
   Room that is left first enlarges the drawings, up to half as much again, and the rest is
   spread over the table rows and the section headings. The phone layout keeps its natural size. */
(function(){
  function fit(){
    var phone=window.matchMedia&&window.matchMedia('screen and (max-width:820px)').matches;
    document.querySelectorAll('article.sheet').forEach(function(s){
      var m=s.querySelector('.content'),f=s.querySelector('.page-foot,.source');
      if(!m||!f)return;
      m.style.zoom='';
      m.querySelectorAll('[data-spread]').forEach(function(e){e.style.paddingTop='';e.style.paddingBottom='';e.style.marginTop='';e.removeAttribute('data-spread');});
      var figs=[].slice.call(m.querySelectorAll('svg[data-fig],figure svg')).filter(function(f){return !f.closest('.duo');});
      figs.forEach(function(f){f.style.width='';f.style.height='';f.style.maxWidth='';});
      if(phone)return;
      function room(){return f.getBoundingClientRect().top-12-m.getBoundingClientRect().bottom;}
      function bad(){return s.scrollHeight>s.clientHeight+1||room()<0;}
      var z=1;m.style.zoom=z;
      while(z>0.86&&bad()){z=Math.round((z-0.02)*100)/100;m.style.zoom=z;}
      s.dataset.fit=z;
      if(z===1&&figs.length){
        var full=m.clientWidth,base=figs.map(function(f){var r=f.getBoundingClientRect();return [r.width,r.height];});
        var size=function(k){figs.forEach(function(f,i){
          f.style.maxWidth='none';f.style.width=base[i][0]*k+'px';f.style.height=base[i][1]*k+'px';
        });};
        var wide=function(){return figs.some(function(f){
          var r=f.getBoundingClientRect(),row=f.closest('.solved');
          return row?r.width>full*.56:(f.closest('.sym')?r.width>full*.31:r.width>full);
        });};
        var k=1;
        while(k<1.5){size(k+.04);if(bad()||wide()){size(k);break;}k=Math.round((k+.04)*100)/100;}
      }
      var heads=[].slice.call(m.children).filter(function(e,i){return i>0&&/^H[2-4]$/.test(e.tagName);});
      var rows=[].slice.call(m.querySelectorAll('tr')).filter(function(r){return r.querySelector('td');}),spare=room();
      if(spare>8&&rows.length){
        var pad=Math.min(spare/rows.length,(heads.length?30:70)*z)/z/2;
        rows.forEach(function(r){[].forEach.call(r.children,function(c){
          var b=parseFloat(getComputedStyle(c).paddingTop)+pad;c.style.paddingTop=b+'px';c.style.paddingBottom=b+'px';c.setAttribute('data-spread','');
        });});
      }
      var left=room();
      var parts=heads.length?heads:[].slice.call(m.children).slice(1);
      if(left>8&&parts.length){
        var add=Math.min(left/parts.length,110*z);
        parts.forEach(function(h){
          if(heads.length)h.style.paddingTop=(add/z)+'px';
          else h.style.marginTop=(parseFloat(getComputedStyle(h).marginTop)+add/z)+'px';
          h.setAttribute('data-spread','');
        });
      }
    });
  }
  window.fitSheets=fit;
  window.addEventListener('load',fit);
  window.addEventListener('beforeprint',fit);
  window.addEventListener('resize',fit);
})();
