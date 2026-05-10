# 📸 IMAGE_NAMING_GUIDE

Estándar único para imágenes de Bigotes y Paticas. Aplica tanto a `local-assets/` como a las claves S3 en DigitalOcean Spaces (`bigotesypaticas/<...>`).

---

## 1. Reglas globales

- **kebab-case**, todo en minúsculas, sin acentos, sin espacios, sin caracteres especiales.
- ASCII solamente: usar `n` en lugar de `ñ`, `a` en lugar de `á`, etc.
- Extensión preferida: **`.webp`** (calidad 82, lossy). Mantener original `.jpg`/`.png` en `local-assets/originals/`.
- Slug = nombre comercial normalizado. Ej: `Croqueta Royal Canin Mini Adulto 2kg` → `royal-canin-mini-adulto-2kg`.

## 2. Productos

Patrón:
```
products/<sku-slug>/<sku-slug>-<role>-<seq>.webp
```

Roles permitidos: `main`, `gallery`, `lifestyle`, `pack`, `nutritional`, `zoom`.

Ejemplos:
```
products/royal-canin-mini-adulto-2kg/royal-canin-mini-adulto-2kg-main.webp
products/royal-canin-mini-adulto-2kg/royal-canin-mini-adulto-2kg-gallery-01.webp
products/royal-canin-mini-adulto-2kg/royal-canin-mini-adulto-2kg-gallery-02.webp
products/royal-canin-mini-adulto-2kg/royal-canin-mini-adulto-2kg-nutritional.webp
```

Tamaños generados por el pipeline (todos WebP):
| Variante | Largo mayor | Uso |
|---|---|---|
| `-thumb` | 200px | listados móviles |
| `-card` | 600px | grilla de productos |
| `-zoom` | 1600px | PDP zoom |
| sin sufijo (`main`) | 1200px | PDP principal |

URL CDN final:
```
https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/products/<sku-slug>/<archivo>.webp
```

## 3. Categorías

```
categories/<categoria-slug>-banner.webp     (1920x600)
categories/<categoria-slug>-hero.webp       (2400x900, retina)
categories/<categoria-slug>-thumb.webp      (400x400, navbar/menu)
categories/<categoria-slug>-icon.webp       (96x96)
```

Ejemplos:
```
categories/perros-banner.webp
categories/gatos-banner.webp
categories/accesorios-banner.webp
```

## 4. Marcas

```
brands/<marca-slug>-logo.webp               (transparente o fondo blanco, 400px)
brands/<marca-slug>-logo-dark.webp          (variante dark mode)
brands/<marca-slug>-banner.webp             (1600x400, opcional)
```

## 5. Banners home / promos

```
uploads/home-hero-<seq>.webp                (1920x800)
uploads/promo-<campania-slug>.webp
uploads/blog-<post-slug>-cover.webp
```

## 6. Compresión y formatos

| Tipo | Formato salida | Calidad | Notas |
|---|---|---|---|
| Foto producto | WebP | 82 | Mantener original RAW |
| Foto lifestyle | WebP | 80 | Permite `srcset` |
| Logo marca | WebP/PNG-8 | lossless | Transparencia |
| Banner | WebP | 78 | Comprimir agresivo |
| Iconos | SVG (preferido) | — | Si no hay SVG, WebP 90 |

## 7. SEO

- El `alt` del `<img>` lo provee el CMS; **no** se usa el filename para SEO directo.
- Pero el filename ayuda al search engine: usar palabras clave del producto.
- Evitar nombres genéricos tipo `IMG_001.jpg`.

## 8. Responsive (`srcset`)

Frontend genera automáticamente:
```html
<img
  src=".../royal-canin-mini-adulto-2kg-card.webp"
  srcset="
    .../royal-canin-mini-adulto-2kg-thumb.webp 200w,
    .../royal-canin-mini-adulto-2kg-card.webp 600w,
    .../royal-canin-mini-adulto-2kg-main.webp 1200w,
    .../royal-canin-mini-adulto-2kg-zoom.webp 1600w
  "
  sizes="(max-width: 640px) 200px, (max-width: 1024px) 600px, 1200px"
  alt="Royal Canin Mini Adulto 2kg"
  loading="lazy"
/>
```

## 9. Validación automática

`scripts/media/validate_naming.py` verifica antes de subir:
- todo lowercase
- sin espacios ni caracteres no-ASCII
- extensión válida (`.webp`, `.png`, `.svg`, `.jpg`)
- estructura de carpeta correcta

Falla rápido y reporta archivos no conformes.

## 10. Anti-patrones

❌ `Royal Canin 2kg.JPG`  
❌ `producto_final_v2_FINAL.png`  
❌ `WhatsApp Image 2026-05-10.jpeg`  
❌ `categoría-perros.webp` (acento)  
✅ `royal-canin-mini-adulto-2kg-main.webp`
