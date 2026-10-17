# Prompts para sincronizar los envíos nacionales fuera de la web

Estos tres cambios no se pueden hacer por API con los permisos que tenemos. Cada
prompt se pega en Claude con acceso al navegador (la app de escritorio de Claude
con control del computador, o Claude en Chrome), con la sesión de Google o de Meta
ya abierta. Los datos de cada prompt están verificados el 17-oct-2026; no hay que
inventar nada.

---

## 1. Google Merchant Center: configuración de envío

```text
Necesito que configures el envío en Google Merchant Center de Bigotes y Paticas
(cuenta 5815728004, sesión de bigotesypaticasdosquebradas@gmail.com). Trabaja en
la interfaz, en Configuración → Envíos y devoluciones. No toques productos, precios,
la política de devoluciones ni ninguna otra sección.

CONTEXTO. Hoy hay UN solo servicio de envío para todo Colombia que dice "gratis
desde $30.000, si no $5.000". Eso es falso fuera de Pereira y Dosquebradas: desde el
16-oct la tienda vende a todo el país y el envío por transportadora se cotiza y se
cobra en la web. El feed ya manda el peso de envío de cada producto
(atributo shipping_weight) y ya no manda envío por producto.

Deja exactamente DOS servicios de envío:

SERVICIO A — "Domicilio Pereira y Dosquebradas"
- Zona: solo Pereira y Dosquebradas (Risaralda). Si la interfaz deja elegir
  ciudades o dibujar la zona, elige esas dos. Si solo deja códigos postales,
  NO adivines: detente y pregúntame. Si solo deja el departamento completo,
  detente y pregúntame antes de usar "Risaralda".
- Costo: pedidos desde $30.000 COP → gratis. Menos de $30.000 → $5.000 COP.
- Sin pedido mínimo.
- Tiempo: preparación 0 días, tránsito 0 a 1 día. Hora de corte 17:00 (Bogotá).
  Días hábiles lunes a sábado.

SERVICIO B — "Envío nacional por transportadora"
- Zona: todo Colombia.
- Costo por PESO del envío (tabla), en COP:
    hasta 1 kg ........ 21.000
    hasta 2 kg ........ 24.000
    hasta 3 kg ........ 26.000
    hasta 5 kg ........ 32.000
    hasta 10 kg ....... 45.000
    hasta 25 kg ....... 48.000
    más de 25 kg ...... 50.000
  (Es la tarifa más barata que da la transportadora a la ciudad más cara entre
  Bogotá, Medellín, Cali, Barranquilla, Bucaramanga, Cartagena, Manizales e
  Ibagué, medida el 17-oct-2026 y redondeada hacia arriba. A la mayoría de
  ciudades el cliente paga igual o menos.)
- Sin envío gratis.
- Tiempo: preparación 1 a 2 días hábiles, tránsito 1 a 5 días hábiles. Hora de
  corte 14:00 (Bogotá). Días hábiles lunes a sábado.

Antes de guardar, muéstrame un resumen de los dos servicios tal como quedarían.
Después de guardar, revisa en Diagnóstico si aparece algún aviso de envío y dímelo.
Si algo de la interfaz no coincide con estas instrucciones, para y pregúntame.
```

---

## 2. Perfil de Empresa de Google (la ficha de Maps)

```text
Entra al Perfil de Empresa de Google de "Bigotes y Paticas Tienda de Mascotas"
(Dosquebradas, sesión de bigotesypaticasdosquebradas@gmail.com) y haz SOLO esto:

1. Descripción: muéstrame la actual. Agrega al final, sin quitar nada, esta frase:
   "Domicilio el mismo día en Pereira y Dosquebradas y envíos a toda Colombia por
   transportadora: cotizas el envío en bigotesypaticas.com y lo pagas con tu
   pedido." Respeta el límite de 750 caracteres; si no cabe, muéstrame una
   propuesta recortando lo menos importante y espera mi aprobación.
2. Atributos de servicio: si existe "Entrega a domicilio" / "Envío" márcalo.
   No cambies la categoría, el nombre, el horario, el teléfono ni la dirección.
3. NO cambies el área de servicio (debe seguir siendo Pereira y Dosquebradas).
4. Publica una novedad (post) con este texto:
   "🚚 ¡Ahora enviamos a toda Colombia! Haz tu pedido en bigotesypaticas.com,
   elige la transportadora, mira el valor y el tiempo de entrega antes de pagar,
   y recibe la guía para rastrear tu paquete. En Pereira y Dosquebradas seguimos
   con domicilio el mismo día, gratis desde $30.000."
   Botón: "Pedir en línea" → https://bigotesypaticas.com
Muéstrame cada cambio antes de guardarlo.
```

---

## 3. Meta: Instagram, Facebook y WhatsApp Business

```text
Ayúdame a actualizar los perfiles de Bigotes y Paticas en Meta. Muéstrame cada
cambio antes de guardarlo.

1. Instagram @bigotesypaticas → Editar perfil → Biografía. Muéstrame la actual y
   propón una nueva de máximo 150 caracteres que conserve lo esencial e incluya
   "Domicilio en Pereira y Dosquebradas 🛵 · Envíos a toda Colombia 🚚". El enlace
   debe seguir siendo https://bigotesypaticas.com.
2. Página de Facebook de Bigotes y Paticas → Información / Detalles. En la
   descripción agrega "Envíos a toda Colombia por transportadora" sin borrar lo
   que hay.
3. WhatsApp Business (en el celular o en business.facebook.com) → Perfil →
   Descripción: agrega "Envíos a toda Colombia". IMPORTANTE: no toques el número,
   la verificación, la cuenta de WhatsApp Business API ni ningún token. Si para
   editar la descripción hay que tocar algo de eso, detente y avísame.
4. No publiques nada nuevo; solo edita perfiles.
```

---

## Lo que YA quedó sincronizado por código (no hay que hacer nada)

| Dónde | Qué dice |
|---|---|
| Tienda web: portada, hero, carrito, ficha de producto, contacto, nosotros, pie de página, zonas | Domicilio en Pereira y Dosquebradas + envíos a toda Colombia |
| Checkout | Elegir "Otra ciudad de Colombia", cotizar, elegir transportadora y pagar |
| Página de pago y confirmación | Transportadora, tiempo, "quién responde por qué" |
| Preguntas frecuentes y términos | Envíos nacionales, pago en línea, responsabilidades |
| llms.txt (lo que leen los buscadores con IA) | Envíos nacionales y cómo se cotizan |
| Portal de clientes | Fuera de la zona: pedir en la web con envío por transportadora |
| Feed de Google Merchant | Peso de envío por producto; ya no declara envío gratis a todo el país |
| Admin | Insignias, panel de guía, registro de envíos, nuevo enlace de pago |
| Correos y WhatsApp al cliente | Confirmación, guía, rastreo y responsabilidades |
