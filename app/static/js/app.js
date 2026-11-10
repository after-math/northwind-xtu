'use strict';

document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

const menuButton = document.querySelector('.menu-toggle');
const menuScrim = document.querySelector('.nav-scrim');
function setMenu(open) {
  document.body.classList.toggle('nav-open', open);
  menuButton?.setAttribute('aria-expanded', String(open));
  menuButton?.setAttribute('aria-label', open ? '收起导航' : '展开导航');
  if (menuScrim) menuScrim.hidden = !open;
}
menuButton?.addEventListener('click', () => setMenu(!document.body.classList.contains('nav-open')));
menuScrim?.addEventListener('click', () => setMenu(false));
document.querySelectorAll('.nav-item').forEach(link => link.addEventListener('click', () => setMenu(false)));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && document.body.classList.contains('nav-open')) {
    setMenu(false);
    menuButton?.focus();
  }
});
window.matchMedia('(min-width: 801px)').addEventListener('change', event => {
  if (event.matches) setMenu(false);
});

const passwordToggle = document.querySelector('.password-toggle');
passwordToggle?.addEventListener('click', () => {
  const input = document.getElementById(passwordToggle.getAttribute('aria-controls'));
  const visible = input.type === 'password';
  input.type = visible ? 'text' : 'password';
  passwordToggle.setAttribute('aria-pressed', String(visible));
  passwordToggle.setAttribute('aria-label', visible ? '隐藏密码' : '显示密码');
});

document.querySelectorAll('.go-back').forEach(button => button.addEventListener('click', () => history.back()));
