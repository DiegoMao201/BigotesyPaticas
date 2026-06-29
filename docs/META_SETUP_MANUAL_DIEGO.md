# Pasos manuales Meta — Diego
Tiempo total estimado: **30 minutos**

---

## 1. Cambiar link Instagram (1 min)
1. Abrir Instagram en el celular → tu perfil → **Editar perfil**
2. En **Sitio web**: eliminar `w.app/Bigotesypaticas`
3. Pegar: `https://mi.bigotesypaticas.com`
4. Guardar

---

## 2. Reemplazar bio Instagram (2 min)
En **Editar perfil → Biografía**, borrar todo y pegar exactamente:

```
🐾 Bigotes y Paticas | Mascotas Pereira y Dosquebradas

🏠 Mall Zamara Plaza, Local 2, Dosquebradas

📦 Domicilio gratis +$30k · Lun–Sáb 10am–7pm

👇 Portal de clientes y pedidos
```

> 148 caracteres — cabe perfecto en los 150 del límite de IG.

---

## 3. Crear Business Manager (10 min)
1. Ir a **business.facebook.com**
2. Clic en **Crear cuenta**
3. Nombre del negocio: `Bigotes y Paticas`
4. Tu nombre: `Diego Mauricio García`
5. Email: `bigotesypaticasdosquebradas@gmail.com`
6. Guardar y verificar el email

---

## 4. Conectar FB Page al Business Manager (3 min)
1. Dentro del BM → **Configuración del negocio**
2. **Cuentas → Páginas → Agregar página**
3. Seleccionar **Reclamar página** → buscar "Bigotes y Paticas"
4. Confirmar en la notificación que llega a tu cuenta FB

---

## 5. Conectar Instagram al Business Manager (3 min)
1. **Configuración del negocio → Cuentas → Cuentas de Instagram**
2. Clic en **Agregar → Conectar tu cuenta de Instagram**
3. Login con `@bigotesypaticas`

---

## 6. Crear catálogo y conectar feed de productos (10 min)
1. En el BM → **Centro de Comercio → Comenzar**
2. Elegir **Catálogo de comercio electrónico**
3. En **Cómo agregar artículos** → **Conectar feed de datos**
4. URL del feed: `https://api.bigotesypaticas.com/v1/catalog/products.xml`
5. Programar actualización: **cada 24 horas**
6. El catálogo empezará a sincronizar ~467 productos automáticamente

---

## 7. Activar Instagram Shopping (5 min)
1. En el catálogo creado → **Configuración → Canales de venta**
2. Activar **Instagram Shopping**
3. Conectar con `@bigotesypaticas`
4. Meta revisará la cuenta (24–48h típicamente)

---

## 8. Activar Facebook Shop (3 min)
1. En **Canales de venta → Facebook Shop**
2. Activar y conectar con tu FB Page "Bigotes y Paticas"

---

## 9. Crear Meta Pixel y pasarme el ID (5 min)
1. En BM → **Eventos → Píxeles → Crear píxel**
2. Nombre: `Bigotes y Paticas Pixel`
3. Copiar el **ID numérico** que aparece (ej: `1234567890123456`)
4. Enviármelo para que actualice la variable `NEXT_PUBLIC_META_PIXEL_ID` en Coolify
5. Una vez actualizado, el pixel empieza a rastrear visitas automáticamente

---

## 10. Configurar webhook de Messenger (5 min)
1. Ir a **developers.facebook.com** → tu App → **Messenger → Configuración**
2. En **Webhooks**: clic en **Editar suscripciones**
3. URL de devolución de llamada: `https://api.bigotesypaticas.com/v1/webhooks/messenger`
4. Token de verificación: `bigotesypaticas_verify`
5. Campos a suscribir: `messages`, `messaging_postbacks`, `messaging_optins`
6. Clic en **Verificar y guardar**

---

## 11. Solicitar verificación FB Page (opcional, esta semana)
1. En FB Page → **Configuración → Verificación de la página**
2. Solicitar verificación gris (negocio local)
3. Documentos: NIT, factura de servicio público
4. Tiempo de respuesta: 5–14 días

---

## Resumen de lo que hace Claude Code automáticamente (ya implementado)

| Feature | Estado |
|---|---|
| Meta Pixel component en tienda web | ✅ listo (activa cuando tengas el Pixel ID) |
| Meta Pixel component en portal | ✅ listo |
| Evento AddToCart | ✅ cuando alguien agrega al carrito |
| Evento InitiateCheckout | ✅ cuando alguien abre WhatsApp para pedir |
| Evento CompleteRegistration | ✅ cuando alguien se registra en el portal |
| Evento Schedule | ✅ cuando alguien agenda una cita |
| Conversion API (server-side) | ✅ Purchase + CompleteRegistration |
| Feed XML de productos | ✅ `api.bigotesypaticas.com/v1/catalog/products.xml` |
| Messenger Get Started + Welcome | ✅ configurado en tu FB Page |
| Messenger Persistent Menu | ✅ 4 opciones en el menú fijo |
| Auto-respuestas Messenger | ✅ 9 intents (precio, domicilio, horarios, etc.) |
| FB Page About + Description | ✅ actualizados |
