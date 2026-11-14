document.addEventListener('DOMContentLoaded', function () {
  var header = document.getElementById('homeTop');
  var toggle = document.getElementById('homeMenuToggle');
  var menu = document.getElementById('homeMenu');

  if (!header) return;

  var updateHeaderState = function () {
    header.classList.toggle('is-scrolled', window.scrollY > 20);
  };

  updateHeaderState();
  window.addEventListener('scroll', updateHeaderState, { passive: true });

  if (!toggle || !menu) return;

  toggle.setAttribute('aria-expanded', 'false');
  toggle.addEventListener('click', function () {
    var isOpen = header.classList.toggle('menu-open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  menu.addEventListener('click', function (event) {
    if (!event.target.closest('a')) return;
    header.classList.remove('menu-open');
    toggle.setAttribute('aria-expanded', 'false');
  });

  var notifications = header.querySelector('[data-reservation-notifications]');
  var notificationsToggle = notifications && notifications.querySelector('[data-notifications-toggle]');
  var notificationsMenu = notifications && notifications.querySelector('[data-notifications-menu]');
  var closeNotifications = function () {
    if (!notificationsMenu || !notificationsToggle) return;
    notificationsMenu.hidden = true;
    notificationsToggle.setAttribute('aria-expanded', 'false');
  };
  notificationsToggle?.addEventListener('click', function (event) {
    event.stopPropagation();
    var open = notificationsMenu.hidden;
    notificationsMenu.hidden = !open;
    notificationsToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('click', function (event) {
    if (notifications && !notifications.contains(event.target)) closeNotifications();
  });
  notifications?.querySelector('[data-notifications-read]')?.addEventListener('click', async function (event) {
    var button = event.currentTarget;
    var csrf = notifications.querySelector('[name=csrfmiddlewaretoken]')?.value || document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || '';
    var response = await fetch(button.dataset.url, {
      method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': decodeURIComponent(csrf) },
    });
    if (!response.ok) return;
    notifications.querySelectorAll('.is-unread').forEach(function (item) { item.classList.remove('is-unread'); });
    notifications.querySelector('[data-notifications-count]')?.remove();
    button.remove();
  });
});
