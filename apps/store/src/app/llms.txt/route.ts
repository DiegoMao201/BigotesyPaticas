/**
 * /llms.txt — el índice de la tienda para los modelos de lenguaje.
 *
 * Es el equivalente de robots.txt+sitemap.xml pero para ChatGPT, Claude, Perplexity
 * y compañía: un solo archivo, en texto plano, que les dice quiénes somos, qué
 * vendemos, dónde estamos y por dónde entrar. Un modelo que rastrea el sitio se
 * encuentra HTML lleno de menús y scripts; aquí encuentra los datos ya masticados,
 * y eso decide si nos nombra cuando alguien pregunta "dónde compro concentrado en
 * Pereira".
 *
 * Complementa a robots.ts, que ya deja pasar a GPTBot, OAI-SearchBot, ChatGPT-User,
 * PerplexityBot, ClaudeBot y Google-Extended.
 *
 * REGLA: aquí no va un solo dato que no esté verificado. Todo lo de abajo sale de
 * los datos estructurados del propio sitio y de la ficha de Google, comprobado el
 * 18-sep-2026. Si algo cambia (horario, teléfono, servicios), se cambia aquí también
 * o el modelo repetirá el dato viejo durante meses.
 */

export const revalidate = 86400;

import { TEXTO } from '@/lib/llms-texto';

export function GET() {
  return new Response(TEXTO, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=86400, stale-while-revalidate=604800',
    },
  });
}
