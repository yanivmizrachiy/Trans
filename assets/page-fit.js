/* Printed A4 sheets: scale each page's content so it fills the sheet above its footer without
   overflowing, then spread what room is left over the table rows and the section headings.
   The phone layout keeps its natural size. */
(function(){
  function fit(){
    var phone=window.matchMedia&&window.matchMedia('screen and (max-width:820px)').matches;
    document.querySelectorAll('article.sheet').forEach(function(s){
      var m=s.querySelector('.content'),f=s.querySelector('.page-foot,.source');
      if(!m||!f)return;
      m.style.zoom='';
      m.querySelectorAll('[data-spread]').forEach(function(e){e.style.paddingTop='';e.style.paddingBottom='';e.removeAttribute('data-spread');});
      if(phone)return;
      function room(){return f.getBoundingClientRect().top-12-m.getBoundingClientRect().bottom;}
      function bad(){return s.scrollHeight>s.clientHeight+1||room()<0;}
      var z=1.12;m.style.zoom=z;
      while(z>0.86&&bad()){z=Math.round((z-0.02)*100)/100;m.style.zoom=z;}
      s.dataset.fit=z;
      var heads=[].slice.call(m.children).filter(function(e,i){return i>0&&/^H[2-4]$/.test(e.tagName);});
      var rows=[].slice.call(m.querySelectorAll('tr')),spare=room();
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
        parts.forEach(function(h){h.style.paddingTop=(add/z)+'px';h.setAttribute('data-spread','');});
      }
    });
  }
  window.fitSheets=fit;
  window.addEventListener('load',fit);
  window.addEventListener('beforeprint',fit);
  window.addEventListener('resize',fit);
})();
