(function(){
  const library=document.getElementById('library'), search=document.getElementById('library-search'), sort=document.getElementById('library-sort'), category=document.getElementById('library-category'), all=document.getElementById('select-all'), count=document.getElementById('selected-count');
  if(!library)return;
  const rows=()=>Array.from(library.querySelectorAll('.library-row'));
  function updateCount(){const n=rows().filter(r=>r.querySelector('.row-select').checked).length;count.textContent=n+' selected'}
  function refresh(){const q=search.value.trim().toLowerCase(),cat=category?category.value:'';rows().forEach(r=>r.hidden=Boolean((q&&!((r.dataset.category+' '+r.dataset.title).includes(q)))||(cat&&r.dataset.category!==cat)));const key=sort.value;rows().sort((a,b)=>{if(key==='status')return b.dataset.enabled.localeCompare(a.dataset.enabled)||a.dataset.title.localeCompare(b.dataset.title);if(key==='question')return a.dataset.title.localeCompare(b.dataset.title);return a.dataset.category.localeCompare(b.dataset.category)||a.dataset.title.localeCompare(b.dataset.title)}).forEach(r=>library.appendChild(r));}
  search.addEventListener('input',refresh);sort.addEventListener('change',refresh);if(category)category.addEventListener('change',refresh);all.addEventListener('change',()=>{rows().filter(r=>!r.hidden).forEach(r=>r.querySelector('.row-select').checked=all.checked);updateCount()});rows().forEach(r=>r.querySelector('.row-select').addEventListener('change',updateCount));
  document.getElementById('library-form').addEventListener('submit',e=>{if(!rows().some(r=>r.querySelector('.row-select').checked)){e.preventDefault();alert('Select at least one item first.')}});refresh();
})();
