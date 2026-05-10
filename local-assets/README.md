# local-assets/

Carpeta local de trabajo para assets que luego se suben a DigitalOcean Spaces.

**No se commitean binarios** (ver `.gitignore`). Solo estructura.

## Subcarpetas

| Carpeta | Uso |
|---|---|
| `originals/` | Imágenes RAW de proveedores/fotógrafo, sin tocar |
| `uploads/` | Drop zone temporal para procesar en lote |
| `optimized/` | Salida del pipeline (WebP, comprimido) — espejo de lo que se sube a S3 |
| `products/` | Imágenes de producto ya organizadas por SKU |
| `categories/` | Banners y hero de categorías |
| `brands/` | Logos de marcas |

## Pipeline

```bash
# 1. Drop originales en local-assets/originals/
# 2. Procesar
python scripts/media/optimize_images.py --src local-assets/originals --dst local-assets/optimized
# 3. Subir a Spaces (prefix bigotesypaticas/)
python scripts/media/upload_to_spaces.py --src local-assets/optimized
```

Reglas de naming en `docs/IMAGE_NAMING_GUIDE.md`.
