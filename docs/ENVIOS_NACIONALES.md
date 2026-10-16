# Envíos nacionales por transportadora (Envia.com)

Procedimiento de despacho de Bigotes y Paticas. Escrito el 16 de octubre de 2026
para que cualquier persona de la tienda lo siga igual, y para copiarlo en otra tienda.

## Cómo llega un pedido nacional

1. El cliente elige en el checkout "Otra ciudad de Colombia", escribe su dirección,
   cotiza y elige transportadora. Paga en línea el pedido con el envío incluido.
2. Recibe en pantalla "Compra exitosa" y un correo con el resumen, el destino y qué sigue.
3. En el admin (Pet Monitor) el pedido aparece con las insignias **PAGADO** y
   **Transportadora · Ciudad**. Al abrirlo, el panel azul "Envío nacional" muestra:
   quién recibe, dirección completa con ciudad y departamento, transportadora
   elegida, tiempo estimado y lo que el cliente pagó por el envío.

Un pedido que todavía no se pagó NO aparece en el admin. Si el cliente abandonó el
pago, aparece a los 30 minutos como **Pago vencido** (o **Pago rechazado**): se abre
y se usa el botón "Nuevo enlace de pago" para mandarle otro por WhatsApp.

## Paso a paso en el admin

| Paso | Botón | Qué pasa |
|---|---|---|
| 1 | Revisar la bandera de riesgo, si la hay | Si es roja, llamar al cliente antes de despachar y marcar "verificado" |
| 2 | "Marcar en revisión" → "Cliente aprobó → listo p/facturar" | Igual que un pedido local |
| 3 | **"Facturar y generar guía"** | Descuenta inventario, crea la venta y pide la guía a Envia. Se abre el WhatsApp para el cliente con el número de guía, el enlace de rastreo y la nota de responsabilidad. El correo con la guía sale solo |
| 4 | "Etiqueta (PDF)" | Imprimir y pegar en el paquete |
| 5 | "Pedir recogida en el local" o llevarlo a un punto | Ver abajo |
| 6 | "Entregado a la transportadora" | Cuando el paquete sale de la tienda; abre otro WhatsApp |
| 7 | "Marcar entregado" | Cuando el rastreo diga entregado. Se le piden al cliente la reseña y los puntos |

Si al facturar la guía no sale (sin saldo en Envia, caída de la transportadora), el
pedido queda facturado igual con una nota interna que dice por qué, y el panel deja
el botón **"Generar guía ahora"** para reintentar.

## Empaque

- **Saco de concentrado de 7 kg o más**: viaja tal cual. Bolsa plástica o vinipel por
  fuera, etiqueta pegada encima con cinta ancha transparente, tapando toda la etiqueta.
  No se mete en caja. Cada saco es un paquete con su propia etiqueta.
- **Todo lo demás** (bolsas de 1 a 3 kg, latas, snacks, medicamentos, accesorios):
  junto en una caja de cartón con relleno para que no se mueva. Una etiqueta por caja.
- Un pedido de saco + cosas sueltas son **dos paquetes** con la misma guía: el sistema
  ya lo calcula así y Envia imprime una etiqueta por paquete.
- Nunca pegar nada encima de un saco que no sea su etiqueta.

## Cómo sale el paquete de la tienda

- **Recogida en el local** (preferida): en el panel, "Pedir recogida en el local", elegir
  fecha y franja (por ejemplo 9:00 a 13:00). La transportadora pasa por Samara Plaza Mall,
  Local 2. El paquete debe estar cerrado y etiquetado antes de la franja.
- **Llevarlo a un punto**: el botón consulta las oficinas que la transportadora publica
  en Envia. Al 16 de octubre de 2026 **ninguna transportadora publica puntos de
  Dosquebradas ni Pereira por la API**, así que para llevarlo a mano hay que confirmar
  la oficina directamente con la transportadora. No se asume ninguna dirección.

## Cancelar una guía

Solo antes de que la transportadora escanee el paquete. Botón "Cancelar esta guía" en el
panel: Envia devuelve el saldo y el panel muestra cuánto. Si ya lo escanearon, no se
puede y el valor de esa guía se pierde.

## Quién responde por qué

La compra es con Bigotes y Paticas: producto, estado y empaque. Desde que la
transportadora recibe el paquete, el transporte y la entrega son responsabilidad de
la transportadora. Ante un retraso, daño o pérdida, el cliente nos escribe y nosotros
presentamos y gestionamos la reclamación ante la transportadora. Este texto va en el
checkout, en la página de pago, en los dos correos, en los WhatsApp de la guía y en
los términos y condiciones. Siempre el mismo.

## Datos de la cuenta

- Remitente en la guía: Bigotes y Paticas, cédula 1088266407, contacto Diego Mauricio
  García Rengifo, representante legal. Samara Plaza Mall, Cl. 15 #3A-07 Local 2,
  Dosquebradas, código DANE 66170000.
- Panel de Envia (saldo, guías, facturas): shipping.envia.com. Cada guía descuenta saldo;
  recargar antes de que se acabe.
- Variables en Coolify (bp-api): `ENVIA_TOKEN`, `ENVIA_ENV=production`,
  `ENVIA_ORIGIN_DOC`. Opcionales: `ENVIA_CARRIERS`, `ENVIA_MARGEN_PCT`.
- Pesos: todos los productos tienen `peso_kg` en sus atributos. Un producto nuevo sin
  peso se estima por su nombre; para afinarlo, escribir `peso_kg` en sus atributos.

## Para replicar en otra tienda

Lo que cambia: el remitente (dirección, DANE, documento, contacto), los tokens de Envia,
los pesos de los productos y los textos con el nombre de la tienda. Lo que no cambia: el
flujo (cotizar, pagar con el envío incluido, facturar = guía, recogida o punto, rastreo),
las reglas de empaque y el reparto de responsabilidades.
