// Reads Flask server-injected runtime config from the <script type="application/json">
// data node in base.html. No window.* access — the script tag is never executed by
// the browser, it's just a data carrier.
const _cfg = JSON.parse(document.getElementById('app-config').textContent);

export const LIFF_ID = _cfg.liffId || null;
export const DEV_MODE = !!_cfg.devMode;
export const SCRIPT_ROOT = _cfg.scriptRoot || '';
