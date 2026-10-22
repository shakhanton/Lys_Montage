/* Галерея «Виконані роботи» з Instagram.
 *
 * Читає assets/data/instagram.json, який раз на добу складає tools/ig_sync.py.
 * Якщо файлу немає або він порожній — у розмітці лишається статична галерея,
 * тож сторінка ніколи не показує порожню секцію (локальний перегляд, збій синку).
 */
(function () {
  var gallery = document.querySelector('[data-ig-gallery]');
  if (!gallery || !window.fetch) return;

  var FEED_URL = gallery.getAttribute('data-ig-gallery') || 'assets/data/instagram.json';
  var MONTHS = ['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
                'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'];

  function formatDate(stamp) {
    // Instagram віддає +0000 без двокрапки — Safari такий рядок не розбирає.
    var iso = String(stamp || '').replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear();
  }

  function badgeFor(type) {
    if (type === 'VIDEO') return '▶ Відео';
    if (type === 'CAROUSEL_ALBUM') return '❏ Галерея';
    return '';
  }

  function buildCard(post) {
    var card = document.createElement('a');
    card.className = 'card gallery-item ig-item';
    card.href = post.permalink;
    card.target = '_blank';
    card.rel = 'noopener';

    var frame = document.createElement('div');
    frame.className = 'ig-frame';

    var img = document.createElement('img');
    img.src = post.src;
    // Підпис уже є в тексті картки — дублювати його в alt означало б читати двічі.
    img.alt = post.title ? 'Публікація: ' + post.title : 'Публікація з Instagram @lys_montag';
    img.loading = 'lazy';
    img.decoding = 'async';
    if (post.width && post.height) {
      img.width = post.width;
      img.height = post.height;
    }
    frame.appendChild(img);

    var badge = badgeFor(post.type);
    if (badge) {
      var tag = document.createElement('span');
      tag.className = 'ig-badge';
      tag.textContent = badge;
      frame.appendChild(tag);
    }
    card.appendChild(frame);

    var body = document.createElement('div');
    body.className = 'ig-body';

    if (post.title) {
      var strong = document.createElement('strong');
      strong.textContent = post.title;
      body.appendChild(strong);
    }
    if (post.text) {
      var text = document.createElement('span');
      text.className = 'ig-text';
      text.textContent = post.text;
      body.appendChild(text);
    }

    var meta = document.createElement('span');
    meta.className = 'ig-meta';
    var date = formatDate(post.timestamp);
    meta.textContent = date ? date + ' · Instagram' : 'Instagram';
    body.appendChild(meta);

    card.appendChild(body);
    return card;
  }

  function render(posts) {
    var fragment = document.createDocumentFragment();
    posts.forEach(function (post) {
      if (post && post.src && post.permalink) fragment.appendChild(buildCard(post));
    });
    if (!fragment.childNodes.length) return;

    gallery.textContent = '';
    gallery.appendChild(fragment);
    gallery.classList.add('ig-live');

    var note = document.querySelector('[data-ig-updated]');
    if (note) note.hidden = false;
  }

  fetch(FEED_URL, { cache: 'no-cache' })
    .then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (data) {
      if (data && Array.isArray(data.posts) && data.posts.length) render(data.posts);
    })
    .catch(function () {
      /* Статична галерея лишається як є — нічого не робимо. */
    });
})();
