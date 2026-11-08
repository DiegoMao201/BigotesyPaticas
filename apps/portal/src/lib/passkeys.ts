/**
 * Huella / Face ID (passkeys) en el navegador, sin librerías: solo convierte entre el
 * JSON que manda la API (base64url) y los ArrayBuffer que pide WebAuthn. 8-nov-2026.
 */
const BASE = '/api/v1/portal/auth';

const aBuf = (s: string) => {
  const b = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0)).buffer;
};
const aB64 = (buf: ArrayBuffer | null) => {
  if (!buf) return null;
  let s = '';
  new Uint8Array(buf).forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d?.detail ?? 'No se pudo completar');
  return d as T;
}

/** ¿Este celular puede usar huella o Face ID para entrar? */
export async function passkeysDisponibles(): Promise<boolean> {
  try {
    return (
      typeof window !== 'undefined' &&
      !!window.PublicKeyCredential &&
      (await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable())
    );
  } catch {
    return false;
  }
}

/** Registra la huella/Face ID de ESTE celular en la cuenta con sesión abierta. */
export async function activarPasskey(nombre?: string) {
  const { options, state } = await post<{ options: any; state: string }>('/passkey/register/options');
  const pk: PublicKeyCredentialCreationOptions = {
    ...options,
    challenge: aBuf(options.challenge),
    user: { ...options.user, id: aBuf(options.user.id) },
    excludeCredentials: (options.excludeCredentials ?? []).map((c: any) => ({ ...c, id: aBuf(c.id) })),
  };
  const cred = (await navigator.credentials.create({ publicKey: pk })) as PublicKeyCredential;
  const res = cred.response as AuthenticatorAttestationResponse;
  return post<{ ok: boolean }>('/passkey/register/verify', {
    state,
    nombre,
    credential: {
      id: cred.id,
      rawId: aB64(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: aB64(res.clientDataJSON),
        attestationObject: aB64(res.attestationObject),
        transports: res.getTransports?.() ?? [],
      },
      clientExtensionResults: cred.getClientExtensionResults?.() ?? {},
    },
  });
}

/** Entra con la huella/Face ID: el celular elige la cuenta, no hay que escribir nada. */
export async function entrarConPasskey<T>() {
  const { options, state } = await post<{ options: any; state: string }>('/passkey/login/options');
  const pk: PublicKeyCredentialRequestOptions = {
    ...options,
    challenge: aBuf(options.challenge),
    allowCredentials: (options.allowCredentials ?? []).map((c: any) => ({ ...c, id: aBuf(c.id) })),
  };
  const cred = (await navigator.credentials.get({ publicKey: pk })) as PublicKeyCredential;
  const res = cred.response as AuthenticatorAssertionResponse;
  return post<T>('/passkey/login/verify', {
    state,
    credential: {
      id: cred.id,
      rawId: aB64(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: aB64(res.clientDataJSON),
        authenticatorData: aB64(res.authenticatorData),
        signature: aB64(res.signature),
        userHandle: aB64(res.userHandle),
      },
      clientExtensionResults: cred.getClientExtensionResults?.() ?? {},
    },
  });
}

export const google = {
  config: () => fetch(`${BASE}/google/config`).then((r) => r.json() as Promise<{ client_id: string | null }>),
  login: <T>(credential: string) => post<T>('/google', { credential }),
  link: <T>(link_token: string, document_id: string, phone: string) => post<T>('/google/link', { link_token, document_id, phone }),
};
