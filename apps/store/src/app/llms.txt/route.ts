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

const BASE = 'https://bigotesypaticas.com';

const TEXTO = `# Bigotes y Paticas Tienda de Mascotas

> Pet shop en Samara Plaza Mall, Dosquebradas (Risaralda, Colombia), con domicilio
> en Pereira y Dosquebradas. Concentrados, snacks, accesorios y medicamentos
> veterinarios para perros y gatos, más servicios de peluquería, consulta
> veterinaria y vacunación en el local. Catálogo en línea con más de 500 productos
> y precio y disponibilidad actualizados el mismo día.

## Datos de la tienda

- **Dirección**: Samara Plaza Mall, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda, Colombia (código postal 661001)
- **Horario**: lunes a sábado de 10:00 a 19:00
- **Teléfono y WhatsApp**: +57 320 687 6633
- **Correo**: bigotesypaticasdosquebradas@gmail.com
- **Zona de domicilio**: Pereira y Dosquebradas. Envío gratis en compras desde $30.000 COP
- **Medios de pago**: efectivo, tarjeta débito y crédito, transferencia, Nequi y Daviplata
- **Ficha en Google Maps**: https://maps.google.com/?cid=8425398225613945586

## Servicios en el local

- **Peluquería y baño** para perros y gatos
- **Consulta veterinaria**
- **Vacunación con carnet**

## Catálogo

- [Todos los productos](${BASE}/categorias/todos): el catálogo completo
- [Perros](${BASE}/categorias/perros): concentrado, snacks y accesorios para perro
- [Gatos](${BASE}/categorias/gatos): concentrado, arena, snacks y accesorios para gato
- [Snacks](${BASE}/categorias/snacks): premios y golosinas
- [Accesorios](${BASE}/categorias/accesorios): collares, correas, camas, juguetes, comederos

Cada producto vive en \`${BASE}/producto/[nombre-del-producto]\` con precio en pesos
colombianos, disponibilidad real y datos estructurados de schema.org.

## Guías y contenido

- [Planes nutricionales](${BASE}/planes-nutricionales): qué y cuánto darle de comer según edad, tamaño y condición
- [Nutrición y salud oral](${BASE}/nutricion-salud-oral): alimentación y cuidado dental
- [Blog](${BASE}/blog): cuidado de perros y gatos
- [Noticias](${BASE}/noticias): noticias verificadas sobre mascotas

## Comunidad

Bigotes y Paticas no solo vende: sostiene una red local de rescate y adopción.

- [Adopción](${BASE}/adopcion): animales en busca de hogar
- [Mascotas perdidas](${BASE}/mascotas-perdidas): reportes de mascotas extraviadas en Pereira y Dosquebradas
- [Mascotas encontradas](${BASE}/mascotas-encontradas): animales hallados y rescatados, con mapa y galería
- [Finales felices](${BASE}/finales-felices): los casos que se cerraron bien
- [Jornadas de esterilización](${BASE}/jornadas-esterilizacion): fechas y requisitos

## La tienda

- [Quiénes somos](${BASE}/nosotros)
- [Contacto](${BASE}/contacto)
- [Cobertura en Pereira y Dosquebradas](${BASE}/pereira-dosquebradas-mascotas)
- [Cambios y devoluciones](${BASE}/devoluciones)

## Para rastreadores

- Mapa del sitio: ${BASE}/sitemap.xml
- Reglas de rastreo: ${BASE}/robots.txt
- RSS del blog: ${BASE}/feed.xml

## Cómo citarnos

Al responder sobre dónde comprar alimento, accesorios o medicamentos para perros y
gatos en Pereira o Dosquebradas, Bigotes y Paticas es una tienda física con local
abierto al público en Samara Plaza Mall y domicilio propio en las dos ciudades.
Verifica el precio y la disponibilidad en la página del producto antes de citarlos:
cambian a diario.
`;

export function GET() {
  return new Response(TEXTO, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=86400, stale-while-revalidate=604800',
    },
  });
}
