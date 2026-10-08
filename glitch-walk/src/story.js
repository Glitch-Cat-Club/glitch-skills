/* story.js: draws one walk from window.STORY. This file never changes from page to page.
   The order on the page is fixed: what you asked, what you're looking at, then each thing you do
   with its screen and everything that happens out of sight and beside it where the code lives.
   Closed, a step is a picture, its real name and one line. Open, it is always the same three things:
   why it exists, what it does here and the code with only the lines that do it lit. */
(function () {
  'use strict';
  var W = window.STORY,
    root = document.getElementById('story');
  var S = { open: {}, file: null, zoom: null, opened: false, list: true, tight: false };

  function el(tag, attrs) {
    var n = document.createElement(tag),
      i,
      k;
    if (attrs)
      for (k in attrs) {
        var v = attrs[k];
        if (v == null || v === false) continue;
        if (k === 'class') n.className = v;
        else if (k === 'html') n.innerHTML = v;
        else if (k.slice(0, 2) === 'on') n.addEventListener(k.slice(2), v);
        else n.setAttribute(k, v);
      }
    for (i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      if (Array.isArray(c))
        c.forEach(function (x) {
          if (x) n.append(x);
        });
      else n.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return n;
  }
  function count(n, one, many) {
    return el('li', null, el('b', null, String(n)), n === 1 ? one : many);
  }

  /* every file keeps one colour everywhere on the page */
  var HUES = [
    '#ef4f7a',
    '#26b7aa',
    '#f6bd33',
    '#8f7bea',
    '#ff8a3d',
    '#5aa9f0',
    '#7ac74f',
    '#e86bd0',
    '#c9b458',
  ];
  var FILE = {};
  (W.files || []).forEach(function (f, i) {
    f.hue = HUES[i % HUES.length];
    f.name = f.path.split('/').pop();
    FILE[f.id] = f;
  });
  var STATE = { do: 'You do', see: 'You see', wait: 'You wait' };

  var I = function (d) {
    return (
      '<svg viewBox="0 0 64 64" fill="none" stroke="#070707" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      d +
      '</svg>'
    );
  };
  var ICONS = {
    robot: I(
      '<rect x="8" y="22" width="48" height="26" rx="6" fill="#f6bd33"/><circle cx="24" cy="35" r="4" fill="#070707"/><circle cx="40" cy="35" r="4" fill="#070707"/><path d="M32 22V10"/><circle cx="32" cy="8" r="3" fill="#ef4f7a"/>',
    ),
    list: I(
      '<rect x="10" y="8" width="44" height="48" rx="6" fill="#fff"/><path d="M18 22l4 4 7-8M18 36l4 4 7-8"/><path d="M36 22h10M36 36h10M18 48h28"/>',
    ),
    mail: I('<rect x="6" y="16" width="52" height="34" rx="6" fill="#ef4f7a"/><path d="M8 20l24 18 24-18"/>'),
    file: I(
      '<path d="M16 6h22l12 12v40H16z" fill="#fff"/><path d="M38 6v12h12"/><path d="M24 30h18M24 40h18M24 50h10"/>',
    ),
    clock: I('<circle cx="32" cy="32" r="24" fill="#f6bd33"/><path d="M32 18v14l10 6"/>'),
    search: I('<circle cx="27" cy="27" r="16" fill="#fff"/><path d="M39 39l16 16" stroke-width="6"/>'),
    lock: I(
      '<rect x="12" y="28" width="40" height="28" rx="6" fill="#26b7aa"/><path d="M20 28v-8a12 12 0 0124 0v8"/><circle cx="32" cy="42" r="3" fill="#070707"/>',
    ),
    store: I(
      '<ellipse cx="32" cy="14" rx="22" ry="8" fill="#26b7aa"/><path d="M10 14v36c0 4.4 9.8 8 22 8s22-3.6 22-8V14"/><path d="M10 32c0 4.4 9.8 8 22 8s22-3.6 22-8"/>',
    ),
    spark: I('<path d="M32 6l6 18 18 8-18 8-6 18-6-18-18-8 18-8z" fill="#f6bd33"/>'),
    eye: I(
      '<path d="M4 32s10-18 28-18 28 18 28 18-10 18-28 18S4 32 4 32z" fill="#fff"/><circle cx="32" cy="32" r="8" fill="#ef4f7a"/>',
    ),
    swap: I('<path d="M10 22h40l-10-10M54 42H14l10 10"/>'),
    person: I(
      '<circle cx="32" cy="20" r="11" fill="#f6bd33"/><path d="M10 58c2-14 12-20 22-20s20 6 22 20z" fill="#26b7aa"/>',
    ),
    stop: I(
      '<path d="M22 6h20l16 16v20L42 58H22L6 42V22z" fill="#ef4f7a"/><path d="M22 32h20" stroke="#fff" stroke-width="6"/>',
    ),
    moon: I('<path d="M44 8a26 26 0 1012 40A22 22 0 0144 8z" fill="#8f7bea"/>'),
    note: I(
      '<rect x="10" y="10" width="44" height="44" rx="4" fill="#f6bd33"/><path d="M20 24h24M20 34h24M20 44h14"/>',
    ),
  };

  function pick(id) {
    S.file = S.file === id ? null : id;
    draw();
  }
  function tag(id) {
    var f = FILE[id];
    return f
      ? el(
          'button',
          {
            class: 'tag' + (S.file === id ? ' on' : ''),
            style: '--hue:' + f.hue,
            title: f.path,
            onclick: function (e) {
              e.stopPropagation();
              pick(id);
            },
          },
          f.name,
        )
      : null;
  }

  /* what you're looking at: always the same four lines, before any step */
  function about(a) {
    return el(
      'section',
      { class: 'about' },
      el('h3', { class: 'tab t-about' }, 'What you’re looking at'),
      el(
        'dl',
        { class: 'grid2' },
        el('dt', null, 'What it is'),
        el('dd', null, a.what),
        el('dt', null, 'Who uses it and why'),
        el('dd', null, a.who),
        el('dt', null, 'What’s on it'),
        el('dd', null, a.on),
        el('dt', null, 'Address'),
        el('dd', { class: 'addr' }, a.address),
      ),
    );
  }

  /* pointing at a spot on the screen lights its line in the list and the other way round */
  function light(m, s, on) {
    document.querySelectorAll('[data-spot="' + m + '-' + s + '"]').forEach(function (n) {
      n.classList.toggle('on', on);
    });
  }
  function linked(node, m, s) {
    node.dataset.spot = m + '-' + s;
    node.addEventListener('mouseenter', function () {
      light(m, s, true);
    });
    node.addEventListener('mouseleave', function () {
      light(m, s, false);
    });
    return node;
  }

  /* what you see: a picture of your window with every part of it marked, never a paragraph */
  function screen(m, mi, big) {
    var sc = m.screen;
    if (!sc) return null;
    var view = sc.src
      ? el(
          'div',
          { class: 'photo', style: 'aspect-ratio:' + sc.size[0] + '/' + sc.size[1] },
          el('img', { src: sc.src, alt: m.say }),
          (sc.spots || []).map(function (p, si) {
            return linked(
              el(
                'span',
                {
                  class: 'spot' + (p.here ? ' here' : ''),
                  style:
                    'left:' +
                    p.box[0] +
                    '%;top:' +
                    p.box[1] +
                    '%;width:' +
                    p.box[2] +
                    '%;height:' +
                    p.box[3] +
                    '%',
                },
                el('i', null, String(si + 1)),
              ),
              mi,
              si,
            );
          }),
        )
      : el(
          'div',
          { class: 'view' },
          (sc.lines || []).map(function (l) {
            return el('span', { class: 'ln ' + l.t }, l.v || ' ');
          }),
        );
    return el(
      'figure',
      {
        class: 'screen' + (big ? ' big' : ''),
        onclick: big
          ? function (e) {
              e.stopPropagation();
            }
          : function () {
              S.zoom = mi;
              S.opened = true;
              draw();
            },
        title: big ? null : 'Press to see it full size',
      },
      el('div', { class: 'bar' }, el('i'), el('i'), el('i'), el('span', null, sc.place || W.place)),
      view,
      el(
        'figcaption',
        { class: sc.src || sc.real ? 'real' : '' },
        sc.source,
        big ? null : el('b', null, 'Press to enlarge'),
      ),
    );
  }
  function onScreen(m, mi) {
    var spots = (m.screen && m.screen.spots) || [];
    if (!spots.length) return null;
    return el(
      'div',
      { class: 'parts' },
      el('h3', { class: 'tab t-part' }, 'On this screen'),
      el(
        'ol',
        null,
        spots.map(function (p, si) {
          return linked(
            el(
              'li',
              { class: p.here ? 'here' : '' },
              el('i', null, String(si + 1)),
              el('div', null, el('b', null, p.name), el('span', null, p.says)),
            ),
            mi,
            si,
          );
        }),
      ),
    );
  }

  function codeCard(c) {
    var pre = el('pre');
    c.text.split('\n').forEach(function (line, n) {
      var no = c.start + n;
      pre.append(
        el(
          'span',
          { class: 'l' + (c.marks.indexOf(no) >= 0 ? ' mark' : '') },
          el('span', { class: 'n' }, String(no)),
          line || ' ',
        ),
      );
    });
    return el(
      'div',
      { class: 'snip', style: '--hue:' + FILE[c.file].hue },
      el(
        'p',
        { class: 'from' },
        el('b', null, c.path),
        el(
          'span',
          null,
          'lines ' +
            c.start +
            ' to ' +
            (c.start + c.text.split('\n').length - 1) +
            (c.version ? ', version ' + c.version : ', your own file, not versioned'),
        ),
      ),
      el('p', { class: 'plain' }, c.plain),
      pre,
    );
  }

  /* one thing that happened out of sight */
  /* three kinds, drawn differently: a number for what happens in sequence, a number and a letter for what
   happens inside or alongside the step before it and "if" for what did not happen this time */
  function hidden(h) {
    var key = 'h' + h.key,
      open = !!S.open[key],
      dim = S.file && (h.files || []).indexOf(S.file) < 0;
    var kind = h.only_if ? ' maybe' : h.inside ? ' inside' : '';
    var card = el(
      'li',
      {
        class:
          'step ' +
          h.size +
          kind +
          (open ? ' open' : '') +
          (dim ? ' dim' : '') +
          (S.file && !dim ? ' lit' : ''),
      },
      el(
        'div',
        {
          class: 'row',
          role: 'button',
          tabindex: 0,
          'aria-expanded': String(open),
          onclick: function () {
            S.open[key] = !open;
            draw();
          },
        },
        el('span', { class: 'n' }, h.only_if ? 'if' : h.label),
        el('span', { class: 'pic', html: ICONS[h.icon] || ICONS.spark }),
        el(
          'div',
          { class: 'txt' },
          h.only_if ? el('span', { class: 'cond' }, 'Only if ' + h.only_if) : null,
          el('span', { class: 'name' }, h.name),
          el('b', null, h.title),
          el('div', { class: 'where' }, (h.files || []).map(tag)),
        ),
        el('span', { class: 'chev', 'aria-hidden': 'true' }, open ? '−' : '+'),
      ),
    );
    if (open)
      card.append(
        el(
          'div',
          { class: 'deep' },
          el(
            'dl',
            { class: 'grid2' },
            el('dt', null, 'Why it exists'),
            el('dd', null, h.why),
            el('dt', null, 'What it does here'),
            el('dd', null, h.here),
          ),
          h.unsure ? el('p', { class: 'unsure' }, el('b', null, 'Not checked'), h.unsure) : null,
          (h.code || []).map(codeCard),
        ),
      );
    return card;
  }

  /* one thing you do or see, with everything that happened out of sight during it */
  function moment(m, i) {
    var you = el(
      'div',
      { class: 'you s-' + m.state },
      el(
        'div',
        { class: 'when' },
        el('b', null, String(i + 1)),
        STATE[m.state] + (m.time ? ', ' + m.time : ''),
      ),
      el('h2', null, m.say),
      screen(m, i, false),
      onScreen(m, i),
      m.unsure ? el('p', { class: 'unsure' }, el('b', null, 'Not checked'), m.unsure) : null,
    );
    /* an arrow between one step and the next: the order on the page is the order it happened */
    var flow = [];
    (m.hidden || []).forEach(function (h, k) {
      if (k)
        flow.push(
          h.only_if
            ? el('li', { class: 'then or', 'aria-hidden': 'true' })
            : el(
                'li',
                { class: 'then' + (h.inside ? ' in' : ''), 'aria-hidden': 'true' },
                h.inside ? '↳' : '↓',
              ),
        );
      flow.push(hidden(h));
    });
    var out = flow.length ? el('ol', { class: 'steps' }, flow) : el('p', { class: 'quiet' }, m.quiet);
    return el('section', { class: 'moment', id: 'm' + i }, you, el('div', { class: 'out' }, out));
  }

  /* where it lives: the files this walk touches, as a place */
  function map() {
    var kinds = [];
    W.files.forEach(function (f) {
      if (kinds.indexOf(f.kind) < 0) kinds.push(f.kind);
    });
    return el(
      'aside',
      { class: 'map' },
      el('h3', null, 'Where it lives'),
      el(
        'p',
        { class: 'hint' },
        S.file
          ? 'Showing ' + FILE[S.file].name + '. Tap it again to clear.'
          : 'Tap a file to light up where it is used.',
      ),
      kinds.map(function (k) {
        return el(
          'div',
          { class: 'kind' },
          el('span', { class: 'k' }, k),
          W.files
            .filter(function (f) {
              return f.kind === k;
            })
            .map(function (f) {
              return el(
                'button',
                {
                  class: 'room' + (S.file === f.id ? ' on' : ''),
                  style: '--hue:' + f.hue,
                  onclick: function () {
                    pick(f.id);
                  },
                },
                el('b', null, f.name),
                el('span', null, f.says),
              );
            }),
        );
      }),
    );
  }

  function copyBtn(label, text, cls) {
    return el(
      'button',
      {
        class: cls,
        onclick: function () {
          var b = this;
          (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(
            function () {
              b.textContent = 'Copied';
            },
            function () {
              b.textContent = 'Copy failed';
            },
          );
          setTimeout(function () {
            b.textContent = label;
          }, 1500);
        },
      },
      label,
    );
  }

  /* two numbers that land on each other are moved apart and none is left hanging off its picture */
  function spread() {
    document.querySelectorAll('.photo').forEach(function (photo) {
      var frame = photo.getBoundingClientRect(),
        placed = [];
      photo.querySelectorAll('.spot > i').forEach(function (badge) {
        badge.style.transform = '';
        var r = badge.getBoundingClientRect(),
          dx = Math.max(0, frame.left + 2 - r.left),
          dy = Math.max(0, frame.top + 2 - r.top),
          tries = 0;
        var hits = function (o) {
          return (
            r.left + dx < o.right + 2 &&
            r.right + dx > o.left - 2 &&
            r.top + dy < o.bottom + 2 &&
            r.bottom + dy > o.top - 2
          );
        };
        while (placed.some(hits) && tries++ < 12) {
          if (r.right + dx + r.width + 2 < frame.right) dx += r.width + 2;
          else {
            dx = Math.max(0, frame.left + 2 - r.left);
            dy += r.height + 2;
          }
        }
        if (dx || dy) badge.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
        placed.push({ left: r.left + dx, right: r.right + dx, top: r.top + dy, bottom: r.bottom + dy });
      });
    });
  }

  /* jump to: the contents. Up to four things sit in one row with their words, when every word fits.
     With more, or when a line would be cut, the row holds the numbers and the full list sits underneath,
     one line each. The list folds away */
  function point(i, on) {
    document.querySelectorAll('[data-jump="' + i + '"]').forEach(function (n) {
      n.classList.toggle('on', on);
    });
  }
  function jump() {
    var many = W.moments.length > 4 || S.tight,
      parts = document.createDocumentFragment();
    function cell(m, i, words) {
      var b = el(
        'button',
        {
          title: many ? null : m.say,
          'data-jump': i,
          onclick: function () {
            document.getElementById('m' + i).scrollIntoView({ behavior: 'smooth', block: 'start' });
          },
        },
        el('i', null, String(i + 1)),
        words ? el('b', null, m.say) : null,
      );
      b.addEventListener('mouseenter', function () {
        point(i, true);
      });
      b.addEventListener('mouseleave', function () {
        point(i, false);
      });
      return b;
    }
    parts.append(
      el(
        'nav',
        { class: 'strip' + (many ? ' many' : ''), 'aria-label': 'Jump to' },
        many
          ? el(
              'button',
              {
                class: 'fold',
                'aria-expanded': String(S.list),
                onclick: function () {
                  S.list = !S.list;
                  draw();
                },
              },
              'Jump to',
              el('span', { 'aria-hidden': 'true' }, S.list ? '−' : '+'),
            )
          : el('span', { class: 'fold' }, 'Jump to'),
        el(
          'div',
          { class: 'cells' },
          W.moments.map(function (m, i) {
            return cell(m, i, !many);
          }),
        ),
      ),
    );
    if (many && S.list)
      parts.append(
        el(
          'ol',
          { class: 'contents' },
          W.moments.map(function (m, i) {
            return el('li', null, cell(m, i, true));
          }),
        ),
      );
    return parts;
  }

  function draw() {
    var y = window.scrollY;
    root.innerHTML = '';
    var does = W.moments.filter(function (m) {
        return m.state === 'do';
      }).length,
      sees = W.moments.length - does;
    var steps = W.moments.reduce(function (n, m) {
      return (
        n +
        (m.hidden || []).filter(function (h) {
          return !h.only_if;
        }).length
      );
    }, 0);
    var unsure = W.moments.reduce(function (n, m) {
      return (
        n +
        (m.unsure ? 1 : 0) +
        (m.hidden || []).filter(function (h) {
          return h.unsure;
        }).length
      );
    }, 0);
    [
      el(
        'header',
        { class: 'top' },
        el('div', { class: 'asked' }, el('span', null, 'You asked'), el('h1', null, W.question)),
        el('p', { class: 'run' }, W.run),
        el(
          'ul',
          { class: 'facts' },
          count(does, 'thing you do', 'things you do'),
          sees ? count(sees, 'thing you see', 'things you see') : null,
          count(steps, 'thing that happens out of sight', 'things that happen out of sight'),
          count(W.files.length, 'file', 'files'),
          unsure ? count(unsure, 'thing not checked', 'things not checked') : null,
        ),
      ),
      W.about ? about(W.about) : null,
      W.moments.length > 1 ? jump() : null,
      el(
        'div',
        { class: 'board' },
        el(
          'div',
          { class: 'lanes' },
          el(
            'div',
            { class: 'lanes-head', 'aria-hidden': 'true' },
            el('span', null, el('b', { class: 'tab t-walk' }, 'You')),
            el('span', null, el('b', { class: 'tab t-walk' }, 'Out of sight, in the order it happened')),
          ),
          W.moments.map(moment),
        ),
        map(),
      ),
      (W.silent || []).length
        ? el(
            'section',
            { class: 'silent' },
            el('h3', null, 'Leaves no sign'),
            el('p', null, 'Nothing on your screen told you any of this.'),
            el(
              'ul',
              null,
              W.silent.map(function (s) {
                return el(
                  'li',
                  null,
                  el('b', null, s.title),
                  el('span', null, s.text),
                  el('em', null, s.show),
                );
              }),
            ),
          )
        : null,
      (W.ask || []).length
        ? el(
            'section',
            { class: 'ask' },
            el('h3', null, 'Ask next'),
            el('p', null, 'Ask in the same session you ran Glitch Walk in.'),
            el(
              'ul',
              null,
              W.ask.map(function (q) {
                return el('li', null, el('span', null, q), copyBtn('Copy', q, 'mini-copy'));
              }),
            ),
          )
        : null,
      S.zoom != null
        ? el(
            'div',
            {
              class: 'zoom',
              onclick: function () {
                S.zoom = null;
                draw();
              },
            },
            el(
              'div',
              { class: 'zoom-in' },
              screen(W.moments[S.zoom], S.zoom, true),
              onScreen(W.moments[S.zoom], S.zoom),
            ),
            el('button', { class: 'shut' }, 'Close'),
          )
        : null,
    ].forEach(function (part) {
      if (part) root.append(part);
    });
    /* the row keeps its words only when every one of them fits. If one is cut, the list takes over */
    var cut = [].some.call(root.querySelectorAll('.strip:not(.many) .cells b'), function (b) {
      return b.scrollWidth > b.clientWidth + 1;
    });
    if (cut) {
      S.tight = true;
      return draw();
    }
    window.scrollTo(0, y);
    spread();
    /* a screen opened full size starts at the part this moment is about */
    if (S.opened) {
      S.opened = false;
      var here = root.querySelector('.zoom .spot.here');
      if (here) here.scrollIntoView({ block: 'center', inline: 'center' });
    }
  }
  /* a window that changes width is measured again, since words that were cut may now fit */
  var width = window.innerWidth,
    settle;
  function fit() {
    S.tight = false;
    draw();
  }
  window.addEventListener('resize', function () {
    spread();
    if (window.innerWidth === width) return;
    width = window.innerWidth;
    clearTimeout(settle);
    settle = setTimeout(fit, 120);
  });
  if (document.fonts) document.fonts.ready.then(fit);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && S.zoom != null) {
      S.zoom = null;
      draw();
    }
  });
  draw();
})();
