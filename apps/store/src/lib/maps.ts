declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    google: any;
    _bpMapsReady?: () => void;
  }
}

const _pending: Array<() => void> = [];

export function loadMapsScript(key: string, cb: () => void): void {
  if (typeof window === 'undefined') return;
  if (window.google?.maps) { cb(); return; }

  _pending.push(cb);
  if (document.getElementById('bp-gmaps')) return;

  window._bpMapsReady = () => {
    const fns = _pending.splice(0);
    fns.forEach(fn => fn());
  };

  const s = document.createElement('script');
  s.id = 'bp-gmaps';
  s.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places&language=es&callback=_bpMapsReady`;
  s.async = true;
  document.head.appendChild(s);
}
