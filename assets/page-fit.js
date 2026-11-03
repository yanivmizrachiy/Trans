/* Printed A4 sheets: scale each page's content so it fills the sheet above its footer without
   overflowing, then spread what room is left over the section headings (SOURCE_OF_TRUTH §כג.14).
   The phone layout keeps its natural size. */
(function(){
  function fit(){
    var phone=window.matchMedia&&window.matchMedia('screen and (max-width:820px)').matches;
    document.querySelectorAll('article.sheet').forEach(function(s){
      var m=s.querySelector('.content'),f=s.querySelector('.page-foot');
      if(!m||!f)return;
      m.style.zoom='';
      m.querySelectorAll('[data-spread]').forEach(function(e){e.style.paddingTop='';e.removeAttribute('data-spread');});
      if(phone)return;
      function room(){return f.getBoundingClientRect().top-12-m.getBoundingClientRect().bottom;}
      function bad(){return s.scrollHeight>s.clientHeight+1||room()<0;}
      var z=1.22;m.style.zoom=z;
      while(z>0.85&&bad()){z=Math.round((z-0.02)*100)/100;m.style.zoom=z;}
      s.dataset.fit=z;
      var heads=[].slice.call(m.children).filter(function(e,i){return i>0&&/^H[2-4]$/.test(e.tagName);});
      var left=room();
      if(left>8&&heads.length){
        var add=Math.min(left/heads.length,46*z);
        heads.forEach(function(h){h.style.paddingTop=(add/z)+'px';h.setAttribute('data-spread','');});
      }
    });
  }
  window.fitSheets=fit;
  window.addEventListener('load',fit);
  window.addEventListener('beforeprint',fit);
  window.addEventListener('resize',fit);
})();
