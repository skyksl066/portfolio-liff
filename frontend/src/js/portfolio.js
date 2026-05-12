import '../css/style.css';
import { initLiff, api, escapeHtml } from './liff-init.js';

'use strict';

const els = {};
let editingId = null;
let cachedHoldings = [];

    // ── Helpers ────────────────────────────────────────────────────────
    const fmtNum = (val) => {
        if (val == null || val === '') return '—';
        const n = Number(val);
        if (!isFinite(n)) return String(val);
        return new Intl.NumberFormat('zh-TW', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 4,
        }).format(n);
    };

    /** Strip ASCII control characters to prevent prompt injection via non-printable chars. */
    const stripCtrl = (s) => String(s).replace(/[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]/g, ' ').trim();

    const fmtDate = (dateStr) => {
        if (!dateStr) return null;
        const d = new Date(dateStr + 'T00:00:00');
        if (isNaN(d)) return dateStr;
        return new Intl.DateTimeFormat('zh-TW', {
            year: 'numeric', month: 'long', day: 'numeric',
        }).format(d);
    };

    const CHEVRON_SVG =
        '<svg class="chevron-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" ' +
        'fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
        '<polyline points="9 18 15 12 9 6"/></svg>';

    document.addEventListener('DOMContentLoaded', async () => {
        cacheEls();
        bindEvents();

        const ok = await initLiff();
        if (!ok) return;

        try {
            await api('/api/me');
        } catch (e) {
            return;
        }

        els.btnNew.disabled = false;
        els.btnStrategy.disabled = false;
        els.btnAnalysis.disabled = false;
        await loadAndRender();
    });

    function cacheEls() {
        els.btnNew = document.getElementById('btn-new');
        els.btnStrategy = document.getElementById('btn-strategy');
        els.btnAnalysis = document.getElementById('btn-analysis');
        els.loading = document.getElementById('loading');
        els.empty = document.getElementById('empty');
        els.error = document.getElementById('error');
        els.groups = document.getElementById('groups');

        els.modalEdit = document.getElementById('modal-edit');
        els.formEdit = document.getElementById('form-edit');
        els.modalTitle = document.getElementById('modal-title');
        els.formError = document.getElementById('form-error');
        els.btnSave = document.getElementById('btn-save');
        els.dlCategories = document.getElementById('dl-categories');
        els.fSymbol = document.getElementById('f-symbol');

        els.modalConfirm = document.getElementById('modal-confirm');
        els.confirmMessage = document.getElementById('confirm-message');

        els.modalStrategy = document.getElementById('modal-strategy');
        els.formStrategy = document.getElementById('form-strategy');
        els.fStrategy = document.getElementById('f-strategy');
        els.strategyError = document.getElementById('strategy-error');
        els.btnStrategySave = document.getElementById('btn-strategy-save');
    }

    function bindEvents() {
        els.btnNew.addEventListener('click', () => openEdit(null));
        els.btnStrategy.addEventListener('click', openStrategy);
        els.btnAnalysis.addEventListener('click', onClickAnalysis);
        els.fSymbol.addEventListener('input', () => { els.fSymbol.value = els.fSymbol.value.toUpperCase(); });

        els.modalEdit.addEventListener('click', (e) => {
            if (e.target.dataset.action === 'close') els.modalEdit.close();
        });
        els.formEdit.addEventListener('submit', onSubmitEdit);
        els.modalEdit.addEventListener('cancel', (e) => {
            // <form method="dialog"> 預設 ESC 也會 submit；攔下避免送出表單
            e.preventDefault();
            els.modalEdit.close();
        });

        els.modalStrategy.addEventListener('click', (e) => {
            if (e.target.dataset.action === 'close') els.modalStrategy.close();
        });
        els.formStrategy.addEventListener('submit', onSubmitStrategy);
        els.modalStrategy.addEventListener('cancel', (e) => {
            e.preventDefault();
            els.modalStrategy.close();
        });
    }

    async function loadAndRender() {
        showLoading(true);
        showError(null);
        try {
            const holdings = await api('/api/holdings');
            renderHoldings(holdings);
        } catch (e) {
            if (e.code === 'FORBIDDEN' || e.code === 'UNAUTHORIZED') return;
            showError(e.message || '載入失敗');
        } finally {
            showLoading(false);
        }
    }

    function renderHoldings(holdings) {
        cachedHoldings = holdings || [];
        els.groups.innerHTML = '';
        if (cachedHoldings.length === 0) {
            els.empty.classList.remove('hidden');
            return;
        }
        els.empty.classList.add('hidden');

        const grouped = {};
        for (const h of cachedHoldings) {
            const key = (h.category && h.category.trim()) ? h.category : '未分類';
            (grouped[key] ||= []).push(h);
        }
        const keys = Object.keys(grouped).sort((a, b) => {
            if (a === '未分類') return 1;
            if (b === '未分類') return -1;
            return a.localeCompare(b, 'zh-Hant');
        });
        const frag = document.createDocumentFragment();
        for (const cat of keys) {
            frag.appendChild(renderGroup(cat, grouped[cat]));
        }
        els.groups.appendChild(frag);

        els.groups.querySelectorAll('[data-edit]').forEach((btn) => {
            btn.addEventListener('click', () => openEdit(btn.dataset.edit));
        });
        els.groups.querySelectorAll('[data-del]').forEach((btn) => {
            btn.addEventListener('click', () => confirmDelete(btn.dataset.del));
        });
    }

    function renderGroup(category, items) {
        const details = document.createElement('details');
        details.className = 'group';
        details.open = true;
        details.innerHTML =
            '<summary class="group-summary">' +
                CHEVRON_SVG +
                '<span class="group-name">' + escapeHtml(category) + '</span>' +
                '<span class="group-count">' + items.length + '</span>' +
            '</summary>' +
            '<div class="cards">' +
                items.map(renderCard).join('') +
            '</div>';
        return details;
    }

    function renderCard(h) {
        const esc = escapeHtml;
        const dateStr = fmtDate(h.purchase_date);
        const metaHtml = dateStr
            ? '<div class="card-meta">買入 ' + esc(dateStr) + '</div>'
            : '';
        const noteHtml = h.note
            ? '<div class="card-note">' + esc(h.note) + '</div>'
            : '';
        return (
            '<div class="card" data-id="' + h.id + '">' +
                '<div class="card-header">' +
                    '<span class="market ' + esc(h.market) + '">' + esc(h.market) + '</span>' +
                    '<span class="symbol">' + esc(h.symbol) + '</span>' +
                    (h.name ? '<span class="name">' + esc(h.name) + '</span>' : '') +
                '</div>' +
                '<div class="card-stats">' +
                    '<div>' +
                        '<div class="card-stat-label">股數</div>' +
                        '<div class="card-stat-value">' + fmtNum(h.shares) + '</div>' +
                    '</div>' +
                    '<div>' +
                        '<div class="card-stat-label">均價</div>' +
                        '<div class="card-stat-value">' + fmtNum(h.avg_price) + '</div>' +
                    '</div>' +
                '</div>' +
                metaHtml +
                noteHtml +
                '<div class="card-actions">' +
                    '<button type="button" data-edit="' + h.id + '">編輯</button>' +
                    '<button type="button" class="btn-del" data-del="' + h.id + '">刪除</button>' +
                '</div>' +
            '</div>'
        );
    }

    function openEdit(id) {
        editingId = id;
        els.formError.classList.add('hidden');
        els.formError.textContent = '';
        refreshCategoriesDatalist();

        if (id == null) {
            els.modalTitle.textContent = '新增持股';
            els.formEdit.reset();
            els.formEdit.market.value = 'TW';
        } else {
            els.modalTitle.textContent = '編輯持股';
            const h = cachedHoldings.find((x) => x.id === id);
            if (!h) {
                loadAndRender();
                return;
            }
            els.formEdit.market.value = h.market;
            els.formEdit.symbol.value = h.symbol || '';
            els.formEdit.name.value = h.name || '';
            els.formEdit.category.value = h.category || '';
            els.formEdit.shares.value = h.shares;
            els.formEdit.avg_price.value = h.avg_price;
            els.formEdit.purchase_date.value = h.purchase_date || '';
            els.formEdit.note.value = h.note || '';
        }
        els.modalEdit.showModal();
    }

    function refreshCategoriesDatalist() {
        const set = new Set();
        for (const h of cachedHoldings) {
            const c = h.category && h.category.trim();
            if (c) set.add(c);
        }
        els.dlCategories.innerHTML = [...set]
            .sort((a, b) => a.localeCompare(b, 'zh-Hant'))
            .map((c) => '<option value="' + escapeHtml(c) + '">')
            .join('');
    }

    async function onSubmitEdit(e) {
        e.preventDefault();
        els.formError.classList.add('hidden');

        const fd = new FormData(els.formEdit);
        const payload = {
            market: fd.get('market'),
            symbol: (fd.get('symbol') || '').trim().toUpperCase(),
            name: (fd.get('name') || '').trim(),
            category: (fd.get('category') || '').trim(),
            shares: fd.get('shares'),
            avg_price: fd.get('avg_price'),
            purchase_date: fd.get('purchase_date') || null,
            note: (fd.get('note') || '').trim(),
        };

        const localErr = validateLocal(payload);
        if (localErr) {
            showFormError(localErr);
            return;
        }

        els.btnSave.disabled = true;
        try {
            if (editingId == null) {
                await api('/api/holdings', { method: 'POST', body: JSON.stringify(payload) });
            } else {
                await api('/api/holdings/' + editingId, { method: 'PUT', body: JSON.stringify(payload) });
            }
            els.modalEdit.close();
            await loadAndRender();
        } catch (err) {
            if (err.code === 'FORBIDDEN' || err.code === 'UNAUTHORIZED') return;
            showFormError(err.message || '儲存失敗');
        } finally {
            els.btnSave.disabled = false;
        }
    }

    function validateLocal(p) {
        if (!['TW', 'US'].includes(p.market)) return '請選擇市場';
        if (!p.symbol) return '請輸入代號';
        if (p.symbol.length > 20) return '代號長度不可超過 20';
        const shares = Number(p.shares);
        const avg = Number(p.avg_price);
        if (!isFinite(shares) || !isFinite(avg)) return '股數 / 均價必須為數字';
        if (shares < 0) return '股數不可小於 0';
        if (avg < 0) return '均價不可小於 0';
        return null;
    }

    function showFormError(msg) {
        els.formError.textContent = msg;
        els.formError.classList.remove('hidden');
    }

    async function confirmDelete(id) {
        const h = cachedHoldings.find((x) => x.id === id);
        els.confirmMessage.textContent = h
            ? '確定要刪除 ' + h.market + ' ' + h.symbol + ' 這筆持股？'
            : '確定要刪除這筆持股？';

        if (!(await waitConfirm())) return;
        try {
            await api('/api/holdings/' + id, { method: 'DELETE' });
            await loadAndRender();
        } catch (err) {
            if (err.code === 'FORBIDDEN' || err.code === 'UNAUTHORIZED') return;
            showError(err.message || '刪除失敗');
        }
    }

    async function onClickAnalysis() {
        els.btnAnalysis.disabled = true;
        try {
            const data = await api('/api/strategy');
            const strategy = (data.strategy || '').trim();

            const holdingLines = cachedHoldings.map((h) => {
                const name = h.name ? ' ' + stripCtrl(h.name) : '';
                return '- ' + h.market + ' ' + h.symbol + name + ' ' + Number(h.shares) + '股 均價' + Number(h.avg_price);
            }).join('\n');

            const parts = [];
            if (strategy) parts.push(stripCtrl(strategy));
            parts.push('## 我的持股清單\n' + (holdingLines || '（尚無持股）'));

            const query = encodeURIComponent(parts.join('\n\n'));
            if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
                let appOpened = false;
                const onHidden = () => { appOpened = true; };
                document.addEventListener('visibilitychange', onHidden, { once: true });
                window.location.href = 'perplexity-app://search?q=' + query;
                setTimeout(() => {
                    document.removeEventListener('visibilitychange', onHidden);
                    if (!appOpened) alert('請先安裝 Perplexity App 再使用此功能');
                }, 1500);
            } else {
                window.open('https://www.perplexity.ai/search?q=' + query, '_blank');
            }
        } catch (err) {
            if (err.code === 'FORBIDDEN' || err.code === 'UNAUTHORIZED') return;
        } finally {
            els.btnAnalysis.disabled = false;
        }
    }

    async function openStrategy() {
        els.strategyError.classList.add('hidden');
        els.strategyError.textContent = '';
        els.fStrategy.value = '';
        els.btnStrategySave.disabled = true;
        els.modalStrategy.showModal();
        try {
            const data = await api('/api/strategy');
            els.fStrategy.value = data.strategy || '';
        } catch (err) {
            if (err.code === 'FORBIDDEN' || err.code === 'UNAUTHORIZED') return;
            els.strategyError.textContent = err.message || '載入策略失敗';
            els.strategyError.classList.remove('hidden');
        } finally {
            els.btnStrategySave.disabled = false;
        }
    }

    async function onSubmitStrategy(e) {
        e.preventDefault();
        els.strategyError.classList.add('hidden');
        const strategy = (els.fStrategy.value || '').trim();
        if (strategy.length > 4000) {
            els.strategyError.textContent = '策略長度不可超過 4000';
            els.strategyError.classList.remove('hidden');
            return;
        }
        els.btnStrategySave.disabled = true;
        try {
            await api('/api/strategy', {
                method: 'PUT',
                body: JSON.stringify({ strategy }),
            });
            els.modalStrategy.close();
        } catch (err) {
            if (err.code === 'FORBIDDEN' || err.code === 'UNAUTHORIZED') return;
            els.strategyError.textContent = err.message || '儲存失敗';
            els.strategyError.classList.remove('hidden');
        } finally {
            els.btnStrategySave.disabled = false;
        }
    }

    function waitConfirm() {
        return new Promise((resolve) => {
            const dlg = els.modalConfirm;
            dlg.addEventListener('close', () => resolve(dlg.returnValue === 'ok'), { once: true });
            dlg.showModal();
        });
    }

    function showLoading(on) {
        const main = document.getElementById('content');
        if (on) {
            main.setAttribute('aria-busy', 'true');
            const skeletonRow = (w1, w2) =>
                '<div style="display:flex;gap:8px;margin-bottom:' + (w2 ? '14' : '0') + 'px">' +
                    '<div class="skeleton" aria-hidden="true" style="width:' + w1 + ';height:' + (w2 ? '22px' : '18px') + '"></div>' +
                    (w2 ? '<div class="skeleton" aria-hidden="true" style="width:' + w2 + ';height:22px"></div>' : '') +
                '</div>';
            const skeletonStat = () =>
                '<div>' +
                    '<div class="skeleton" aria-hidden="true" style="width:28px;height:10px;margin-bottom:5px"></div>' +
                    '<div class="skeleton" aria-hidden="true" style="width:72px;height:20px"></div>' +
                '</div>';
            els.loading.innerHTML = [0, 1, 2].map(() =>
                '<div class="skeleton-card" style="margin-bottom:8px">' +
                    skeletonRow('42px', '68px') +
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:2px">' +
                        skeletonStat() + skeletonStat() +
                    '</div>' +
                '</div>'
            ).join('');
            els.loading.classList.remove('hidden');
        } else {
            main.setAttribute('aria-busy', 'false');
            els.loading.classList.add('hidden');
            els.loading.innerHTML = '';
        }
    }

    function showError(msg) {
        if (!msg) {
            els.error.classList.add('hidden');
            els.error.textContent = '';
        } else {
            els.error.textContent = msg;
            els.error.classList.remove('hidden');
        }
    }
