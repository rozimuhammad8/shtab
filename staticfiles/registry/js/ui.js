/* ==========================================================================
 * Shtab ma'lumotlar bazasi - interfeys skriptlari
 *
 *  1. iOS uslubidagi maxsus ochiluvchi ro'yxat (custom select):
 *     "shisha" panel, kaskad animatsiya, ripple effekti, chip ko'rinishidagi
 *     tanlovlar, qidiruv va klaviatura bilan boshqarish.
 *  2. Mavzu (yorug'/qorong'i) almashtirish.
 *  3. Xizmatlar jadvaliga qator qo'shish/o'chirish (Django formset).
 *  4. Joyida tahrirlash: «Tahrirlash» / «Saqlash» tugmalari.
 *
 * JavaScript ishlamasa ham sahifalar to'liq ishlashda davom etadi:
 * `<select>` elementlari o'z holida qoladi.
 * ========================================================================== */
(function () {
    'use strict';

    var SVG_CARET = '<svg class="cs-caret" viewBox="0 0 12 8" aria-hidden="true">' +
        '<polyline points="1 1 6 6 11 1"/></svg>';
    var SVG_TICK = '<svg class="cs-tick" viewBox="0 0 14 10" aria-hidden="true">' +
        '<polyline points="1 5 5 9 13 1"/></svg>';
    var SVG_SEARCH = '<svg viewBox="0 0 16 16" aria-hidden="true">' +
        '<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>';

    /** Ko'p tanlovda tugmada nechta chip ko'rsatilsin */
    var CHIP_LIMIT = 2;

    var ochiq = null;   // hozir ochiq bo'lgan ro'yxat
    var raqam = 0;

    /* --------------------------------------------------------------------
     * Ripple (bosilganda tarqaladigan to'lqin)
     * ------------------------------------------------------------------ */

    function ripple(e, element) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        var rect = element.getBoundingClientRect();
        var oldi = element.querySelector('.cs-ripple');
        if (oldi) oldi.remove();

        var d = Math.max(rect.width, rect.height);
        var span = document.createElement('span');
        span.className = 'cs-ripple';
        span.style.width = span.style.height = d + 'px';
        // Klaviatura bilan bosilganda koordinata bo'lmaydi - markazdan chiqadi.
        var x = e && e.clientX ? e.clientX - rect.left : rect.width / 2;
        var y = e && e.clientY ? e.clientY - rect.top : rect.height / 2;
        span.style.left = (x - d / 2) + 'px';
        span.style.top = (y - d / 2) + 'px';
        element.appendChild(span);
        setTimeout(function () { span.remove(); }, 480);
    }

    /* --------------------------------------------------------------------
     * 1. Maxsus ochiluvchi ro'yxat
     * ------------------------------------------------------------------ */

    function CustomSelect(select) {
        this.select = select;
        this.multi = select.multiple;
        this.id = 'cs-' + (++raqam);
        // Yorliq: `data-label="Mahalla"` bo'lsa iOS sozlamalari uslubida
        // chapda doimiy matn, o'ngda tanlangan qiymat ko'rinadi.
        this.yorliq = select.dataset.label || '';
        // Qidiruv maydoni 8 dan ortiq variant bo'lganda paydo bo'ladi.
        this.qidiruvli = select.options.length > 8;
        this.qur();
    }

    CustomSelect.prototype.qur = function () {
        var s = this.select;
        var oram = document.createElement('div');
        oram.className = 'custom-select';

        this.tugma = document.createElement('button');
        this.tugma.type = 'button';
        this.tugma.className = 'cs-button' + (this.yorliq ? '' : ' no-label');
        this.tugma.setAttribute('aria-haspopup', 'listbox');
        this.tugma.setAttribute('aria-expanded', 'false');
        this.tugma.innerHTML =
            (this.yorliq ? '<span class="cs-label"></span>' : '') +
            '<span class="cs-value-group">' +
                (this.multi ? '<span class="cs-chips"></span>'
                            : '<span class="cs-value"></span>') +
                SVG_CARET +
            '</span>';
        if (this.yorliq) this.tugma.querySelector('.cs-label').textContent = this.yorliq;

        this.panel = document.createElement('div');
        this.panel.className = 'cs-panel';

        if (this.multi) {
            var bosh = document.createElement('div');
            bosh.className = 'cs-header';
            bosh.innerHTML = '<button type="button" data-hammasi>Hammasini tanlash</button>' +
                '<button type="button" data-tozalash>Tozalash</button>';
            this.panel.appendChild(bosh);
            var self0 = this;
            bosh.querySelector('[data-hammasi]').addEventListener('click', function () {
                self0.hammasi(true);
            });
            bosh.querySelector('[data-tozalash]').addEventListener('click', function () {
                self0.hammasi(false);
            });
        }

        if (this.qidiruvli) {
            var qid = document.createElement('div');
            qid.className = 'cs-search';
            qid.innerHTML = SVG_SEARCH +
                '<input type="text" autocomplete="off" spellcheck="false" ' +
                'placeholder="Qidirish..." aria-label="Variantlar orasidan qidirish">';
            this.panel.appendChild(qid);
            this.qidiruv = qid.querySelector('input');
        }

        this.royxat = document.createElement('ul');
        this.royxat.className = 'cs-list';
        this.royxat.setAttribute('role', 'listbox');
        this.royxat.id = this.id;
        if (this.multi) this.royxat.setAttribute('aria-multiselectable', 'true');
        this.panel.appendChild(this.royxat);

        this.tugma.setAttribute('aria-controls', this.id);

        // `<select>` ni yashirib, uning o'rniga yangi tuzilmani qo'yamiz.
        s.parentNode.insertBefore(oram, s);
        oram.appendChild(this.tugma);
        oram.appendChild(this.panel);
        oram.appendChild(s);
        s.classList.add('sr-only');
        s.setAttribute('tabindex', '-1');
        s.setAttribute('aria-hidden', 'true');
        this.oram = oram;

        this.variantlarniQur();
        this.yangila();
        this.hodisalar();
    };

    CustomSelect.prototype.variantlarniQur = function () {
        var self = this;
        this.royxat.innerHTML = '';
        this.elementlar = [];

        Array.prototype.forEach.call(this.select.options, function (opt, i) {
            var matn = opt.textContent.trim();
            var li = document.createElement('li');
            li.className = 'cs-option';
            li.setAttribute('role', 'option');
            li.dataset.index = i;
            li.title = matn;
            li.innerHTML = '<span class="cs-option-text"></span>' + SVG_TICK;
            li.querySelector('.cs-option-text').textContent = matn;
            if (opt.disabled) {
                li.setAttribute('aria-disabled', 'true');
                li.style.opacity = '.5';
            }
            self.royxat.appendChild(li);
            self.elementlar.push(li);
        });

        this.bosh = document.createElement('li');
        this.bosh.className = 'cs-empty';
        this.bosh.textContent = 'Topilmadi';
        this.bosh.hidden = true;
        this.royxat.appendChild(this.bosh);
    };

    /** Tugmadagi matn/chiplarni va belgilangan variantlarni joyiga qo'yadi. */
    CustomSelect.prototype.yangila = function () {
        var s = this.select;
        var tanlangan = [];

        Array.prototype.forEach.call(s.options, function (opt, i) {
            var li = this.elementlar[i];
            if (!li) return;
            li.classList.toggle('is-selected', opt.selected);
            li.setAttribute('aria-selected', opt.selected ? 'true' : 'false');
            // Bo'sh qiymatli variant ("-- Barchasi --") tanlov hisoblanmaydi.
            if (opt.selected && opt.value !== '') tanlangan.push(opt.textContent.trim());
        }, this);

        if (this.multi) {
            this.chiplarniChiz(tanlangan);
        } else {
            var qiymat = this.tugma.querySelector('.cs-value');
            if (tanlangan.length) {
                qiymat.textContent = tanlangan[0];
                this.tugma.classList.remove('is-placeholder');
            } else {
                // Bo'sh holatda birinchi variant matni ("-- Barchasi --") chiqadi.
                var birinchi = s.options[0];
                qiymat.textContent = s.dataset.placeholder
                    || (birinchi ? birinchi.textContent.trim() : 'Tanlanmagan');
                this.tugma.classList.add('is-placeholder');
            }
        }
    };

    CustomSelect.prototype.chiplarniChiz = function (tanlangan) {
        var joy = this.tugma.querySelector('.cs-chips');
        joy.innerHTML = '';

        if (!tanlangan.length) {
            var bosh = document.createElement('span');
            bosh.className = 'cs-value';
            bosh.textContent = this.select.dataset.placeholder || 'Tanlanmagan';
            joy.appendChild(bosh);
            this.tugma.classList.add('is-placeholder');
            return;
        }

        this.tugma.classList.remove('is-placeholder');
        tanlangan.slice(0, CHIP_LIMIT).forEach(function (matn) {
            var chip = document.createElement('span');
            chip.className = 'cs-chip';
            chip.textContent = matn;
            chip.title = matn;
            joy.appendChild(chip);
        });
        if (tanlangan.length > CHIP_LIMIT) {
            var yana = document.createElement('span');
            yana.className = 'cs-chip cs-chip-more';
            yana.textContent = '+' + (tanlangan.length - CHIP_LIMIT);
            yana.title = tanlangan.join(', ');
            joy.appendChild(yana);
        }
    };

    CustomSelect.prototype.och = function () {
        if (ochiq && ochiq !== this) ochiq.yop();
        ochiq = this;
        this.oram.classList.add('is-open');
        this.tugma.setAttribute('aria-expanded', 'true');

        // Ekranning pastida joy yetmasa ro'yxat yuqoriga ochiladi.
        var joy = window.innerHeight - this.tugma.getBoundingClientRect().bottom;
        this.oram.classList.toggle('drop-up', joy < 320);

        if (this.qidiruv) {
            this.qidiruv.value = '';
            this.suz('');
            this.qidiruv.focus();
        }
        var faol = this.royxat.querySelector('.cs-option.is-selected:not([hidden])')
            || this.royxat.querySelector('.cs-option:not([hidden])');
        this.faollashtir(faol);
    };

    CustomSelect.prototype.yop = function (fokus) {
        this.oram.classList.remove('is-open');
        this.tugma.setAttribute('aria-expanded', 'false');
        this.faollashtir(null);
        if (ochiq === this) ochiq = null;
        if (fokus) this.tugma.focus();
    };

    CustomSelect.prototype.faollashtir = function (li) {
        if (this.faol) this.faol.classList.remove('is-active');
        this.faol = li || null;
        if (!li) {
            this.royxat.removeAttribute('aria-activedescendant');
            return;
        }
        li.classList.add('is-active');
        // Ro'yxat ichida ko'rinib turishi uchun surib qo'yamiz.
        var r = li.getBoundingClientRect();
        var p = this.royxat.getBoundingClientRect();
        if (r.top < p.top) this.royxat.scrollTop -= (p.top - r.top);
        else if (r.bottom > p.bottom) this.royxat.scrollTop += (r.bottom - p.bottom);
    };

    CustomSelect.prototype.tanla = function (li, e) {
        if (!li || li.getAttribute('aria-disabled') === 'true') return;
        var opt = this.select.options[li.dataset.index];
        if (!opt) return;

        ripple(e, li);

        if (this.multi) {
            opt.selected = !opt.selected;
        } else {
            this.select.selectedIndex = li.dataset.index;
        }
        this.select.dispatchEvent(new Event('change', { bubbles: true }));
        this.yangila();

        // Bir tanlovli ro'yxat tanlangach yopiladi (belgi ko'rinishi uchun kechikish bilan).
        if (!this.multi) {
            var self = this;
            setTimeout(function () { self.yop(true); }, 130);
        }
    };

    CustomSelect.prototype.hammasi = function (holat) {
        Array.prototype.forEach.call(this.select.options, function (opt) {
            if (opt.value !== '' && !opt.disabled) opt.selected = holat;
        });
        this.select.dispatchEvent(new Event('change', { bubbles: true }));
        this.yangila();
    };

    CustomSelect.prototype.suz = function (matn) {
        var q = matn.trim().toLowerCase();
        var bor = 0;
        this.elementlar.forEach(function (li) {
            var mos = !q || li.querySelector('.cs-option-text')
                .textContent.toLowerCase().indexOf(q) !== -1;
            li.hidden = !mos;
            if (mos) bor++;
        });
        this.bosh.hidden = bor > 0;
    };

    CustomSelect.prototype.hodisalar = function () {
        var self = this;

        this.tugma.addEventListener('click', function (e) {
            ripple(e, self.tugma);
            self.oram.classList.contains('is-open') ? self.yop(true) : self.och();
        });

        this.royxat.addEventListener('click', function (e) {
            var li = e.target.closest('.cs-option');
            if (li) self.tanla(li, e);
        });

        // Sichqoncha ustiga kelganda faol variantni ko'chiramiz.
        this.royxat.addEventListener('mousemove', function (e) {
            var li = e.target.closest('.cs-option');
            if (li && li !== self.faol) self.faollashtir(li);
        });

        if (this.qidiruv) {
            this.qidiruv.addEventListener('input', function () {
                self.suz(this.value);
                self.faollashtir(self.royxat.querySelector('.cs-option:not([hidden])'));
            });
        }

        // Klaviatura bilan boshqarish
        this.oram.addEventListener('keydown', function (e) {
            var ochiqmi = self.oram.classList.contains('is-open');

            if (e.key === 'Escape') {
                if (ochiqmi) { e.stopPropagation(); self.yop(true); }
                return;
            }
            if (e.key === 'Tab') {
                if (ochiqmi) self.yop();
                return;
            }
            if (!ochiqmi) {
                if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].indexOf(e.key) !== -1) {
                    e.preventDefault();
                    self.och();
                }
                return;
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                self.tanla(self.faol, null);
                return;
            }
            if (e.key === ' ' && self.multi && e.target !== self.qidiruv) {
                e.preventDefault();
                self.tanla(self.faol, null);
                return;
            }
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                var royxat = self.elementlar.filter(function (li) { return !li.hidden; });
                if (!royxat.length) return;
                var i = royxat.indexOf(self.faol);
                i = e.key === 'ArrowDown'
                    ? (i < 0 ? 0 : Math.min(i + 1, royxat.length - 1))
                    : (i < 0 ? royxat.length - 1 : Math.max(i - 1, 0));
                self.faollashtir(royxat[i]);
                return;
            }
            if (e.key === 'Home' || e.key === 'End') {
                var r2 = self.elementlar.filter(function (li) { return !li.hidden; });
                if (r2.length) {
                    e.preventDefault();
                    self.faollashtir(e.key === 'Home' ? r2[0] : r2[r2.length - 1]);
                }
            }
        });

        // Tashqi kod `<select>` ni o'zgartirsa, ko'rinishni yangilaymiz.
        this.select.addEventListener('cs:refresh', function () {
            self.variantlarniQur();
            self.yangila();
        });
    };

    /* --------------------------------------------------------------------
     * 2. Mavzu (theme)
     * ------------------------------------------------------------------ */

    function mavzuniSozla() {
        var tugma = document.querySelector('.theme-toggle');
        if (!tugma) return;
        tugma.addEventListener('click', function () {
            var hozir = document.documentElement.getAttribute('data-theme');
            if (!hozir) {
                // Hali tanlanmagan bo'lsa - tizim sozlamasining teskarisiga o'tamiz.
                hozir = window.matchMedia('(prefers-color-scheme: dark)').matches
                    ? 'dark' : 'light';
            }
            var yangi = hozir === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', yangi);
            try { localStorage.setItem('shtab-mavzu', yangi); } catch (e) { /* e'tiborsiz */ }
        });
    }

    /* --------------------------------------------------------------------
     * 3. Formset: xizmat qatorlarini qo'shish/o'chirish
     * ------------------------------------------------------------------ */

    function formsetniSozla() {
        document.querySelectorAll('[data-formset]').forEach(function (oram) {
            var prefiks = oram.dataset.formset;
            var jami = document.getElementById('id_' + prefiks + '-TOTAL_FORMS');
            var namuna = oram.querySelector('[data-formset-empty]');
            var qoshish = document.querySelector('[data-formset-add="' + prefiks + '"]');
            if (!jami || !namuna || !qoshish) return;

            var joy = oram.querySelector('[data-formset-rows]');

            qoshish.addEventListener('click', function () {
                var n = parseInt(jami.value, 10);
                var html = namuna.innerHTML.replace(/__prefix__/g, n);
                var div = document.createElement('div');
                div.innerHTML = html.trim();
                var qator = div.firstElementChild;
                joy.appendChild(qator);
                jami.value = n + 1;
                // Yangi qatordagi `<select>` larni ham maxsus ko'rinishga o'tkazamiz.
                qator.querySelectorAll('select').forEach(function (s) {
                    if (!s.closest('.custom-select')) new CustomSelect(s);
                });
                var birinchi = qator.querySelector('.cs-button, input');
                if (birinchi) birinchi.focus();
            });

            // "O'chirish" tugmasi: bazada bor qatorda DELETE belgilanadi,
            // yangi (hali saqlanmagan) qator esa butunlay olib tashlanadi.
            oram.addEventListener('click', function (e) {
                var tugma = e.target.closest('.row-remove');
                if (!tugma) return;
                var qator = tugma.closest('.formset-row');
                var ochir = qator.querySelector('input[type="checkbox"][name$="-DELETE"]');
                if (ochir) {
                    ochir.checked = !ochir.checked;
                    qator.classList.toggle('is-deleted', ochir.checked);
                } else {
                    qator.remove();
                    jami.value = parseInt(jami.value, 10) - 1;
                }
            });
        });
    }

    /* --------------------------------------------------------------------
     * 4. Joyida tahrirlash (inline edit)
     *
     * «Tahrirlash» bosilganda formaga `.is-editing` klassi qo'shiladi -
     * qiymatlar o'rniga forma maydonlari ko'rinadi. «Saqlash» oddiy POST,
     * «Bekor qilish» esa sahifani qayta yuklab o'zgarishlarni tashlaydi.
     * ------------------------------------------------------------------ */

    function joyidaTahrir() {
        var forma = document.querySelector('[data-inline-edit]');
        if (!forma) return;

        var ozgardi = false;
        forma.addEventListener('input', function () { ozgardi = true; });
        forma.addEventListener('change', function () { ozgardi = true; });

        function boshla() {
            forma.classList.add('is-editing');
            // Maxsus ro'yxatlar yashirin holatda yasalgan bo'lsa,
            // kengligini qaytadan hisoblash uchun hodisa yuboramiz.
            window.dispatchEvent(new Event('resize'));
            var birinchi = forma.querySelector(
                '.rw input:not([type=hidden]), .rw textarea, .rw .cs-button'
            );
            if (birinchi) birinchi.focus();
        }

        forma.querySelectorAll('[data-tahrir-boshla]').forEach(function (t) {
            t.addEventListener('click', boshla);
        });

        forma.querySelectorAll('[data-tahrir-bekor]').forEach(function (t) {
            t.addEventListener('click', function () {
                if (ozgardi && !window.confirm(
                        "Saqlanmagan o'zgarishlar bor. Bekor qilinsinmi?")) {
                    return;
                }
                // Sahifani qaytadan yuklab, saqlanmagan qiymatlarni tashlaymiz.
                window.location = window.location.pathname;
            });
        });

        // Tahrirlash holatida sahifadan chiqib ketishdan ogohlantiramiz.
        window.addEventListener('beforeunload', function (e) {
            if (forma.classList.contains('is-editing') && ozgardi) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Saqlashda ogohlantirish kerak emas.
        forma.addEventListener('submit', function () { ozgardi = false; });

        // Xato bilan qaytgan sahifa allaqachon tahrirlash holatida bo'ladi -
        // birinchi xatoli maydonga o'tamiz.
        if (forma.classList.contains('is-editing')) {
            var xatoli = forma.querySelector('.has-error');
            if (xatoli) xatoli.scrollIntoView({ block: 'center' });
        }
    }

    /* --------------------------------------------------------------------
     * 5. Mahalla o'zgarganda oilalar ro'yxatini yangilash
     * ------------------------------------------------------------------ */

    function oilalarniBogla() {
        var mahalla = document.querySelector('select[name="mahalla"][data-oila-manba]');
        var oila = document.querySelector('select[name="oila"]');
        if (!mahalla || !oila) return;

        var manba = mahalla.dataset.oilaManba;

        mahalla.addEventListener('change', function () {
            var id = mahalla.value;
            if (!id) return;

            fetch(manba + '?mahalla=' + encodeURIComponent(id), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            })
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (d) {
                    if (!d) return;
                    var tanlangan = oila.value;
                    oila.innerHTML = '';
                    var bosh = document.createElement('option');
                    bosh.value = '';
                    bosh.textContent = '— Oila tanlanmagan —';
                    oila.appendChild(bosh);
                    d.oilalar.forEach(function (o) {
                        var opt = document.createElement('option');
                        opt.value = o.id;
                        opt.textContent = o.matn;
                        if (String(o.id) === tanlangan) opt.selected = true;
                        oila.appendChild(opt);
                    });
                    // Maxsus ro'yxatni yangi variantlar bilan qayta chizamiz.
                    oila.dispatchEvent(new Event('cs:refresh'));
                })
                .catch(function () { /* tarmoq xatosi - oddiy select qoladi */ });
        });
    }

    /* --------------------------------------------------------------------
     * Ishga tushirish
     * ------------------------------------------------------------------ */

    function boshla() {
        document.querySelectorAll('select[data-select]').forEach(function (s) {
            if (!s.closest('.custom-select')) new CustomSelect(s);
        });

        // Tashqariga bosilganda ochiq ro'yxat yopiladi.
        document.addEventListener('click', function (e) {
            if (ochiq && !e.target.closest('.custom-select')) ochiq.yop();
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && ochiq) ochiq.yop(true);
        });

        mavzuniSozla();
        formsetniSozla();
        oilalarniBogla();
        joyidaTahrir();

        // O'chirishdan oldin tasdiqlash
        document.querySelectorAll('[data-confirm]').forEach(function (f) {
            f.addEventListener('submit', function (e) {
                if (!window.confirm(f.dataset.confirm)) e.preventDefault();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boshla);
    } else {
        boshla();
    }
})();
