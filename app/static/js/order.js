'use strict';
(() => {
  const body=document.getElementById('order-lines'), template=document.getElementById('line-template');
  const freight=document.getElementById('freight');
  function calculate() {
    let sum=0;
    body.querySelectorAll('tr').forEach(row=>{
      const option=row.querySelector('select').selectedOptions[0];
      const price=Number(option?.dataset.price||0), stock=Number(option?.dataset.stock||0);
      const quantity=Number(row.querySelector('.line-quantity').value||0), discount=Number(row.querySelector('.line-discount').value||0);
      const total=price*quantity*(1-discount);
      row.querySelector('.line-stock').textContent=option?.value?stock:'—';
      row.querySelector('.line-price').textContent=option?.value?price.toFixed(2):'—';
      row.querySelector('.line-total').textContent=Number.isFinite(total)?total.toFixed(2):'—';
      if(Number.isFinite(total)) sum+=total;
    });
    document.getElementById('estimated-total').textContent=(sum+Number(freight.value||0)).toFixed(2);
  }
  function add(item={}) {
    if (body.children.length>=100) return;
    const row=template.content.cloneNode(true).querySelector('tr');
    if(item.product_id) row.querySelector('select').value=item.product_id;
    if(item.quantity) row.querySelector('.line-quantity').value=item.quantity;
    if(item.discount) row.querySelector('.line-discount').value=item.discount;
    row.addEventListener('input',calculate); row.addEventListener('change',calculate);
    row.querySelector('.remove-line').addEventListener('click',()=>{row.remove();if(!body.children.length)add();calculate();});
    body.appendChild(row);calculate();
  }
  document.getElementById('add-line').addEventListener('click',()=>add());
  freight.addEventListener('input',calculate);
  const submitted=JSON.parse(document.getElementById('submitted-lines').dataset.lines);
  if(submitted.length) submitted.forEach(add);else add();
  document.getElementById('order-form').addEventListener('submit',event=>{
    const ids=Array.from(body.querySelectorAll('select')).map(x=>x.value);
    if(new Set(ids).size!==ids.length){event.preventDefault();window.alert('同一商品只能添加一次，请合并购买数量。');}
  });
})();
