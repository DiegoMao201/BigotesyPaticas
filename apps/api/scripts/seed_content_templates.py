#!/usr/bin/env python3
"""Seed de 12 templates editoriales para el content engine Sprint 6A.

Uso:
    python scripts/seed_content_templates.py
    python scripts/seed_content_templates.py --reset  # Borra y re-inserta
"""
from __future__ import annotations
import argparse, os, sys
import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://postgres:JE7zr39ODs6ZHrTgzH1OWgsvt5J005hid73BfIMjiIKit9KxqJSNXh3KOHowMXwb@l0k0kck8cwck4goskcs0scsg:5432/bp_prod"
).replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")

TEMPLATES = [
    {
        "code": "product_hero",
        "name": "Producto Hero — Editorial",
        "category": "product",
        "visual_style": "apple_minimal",
        "visual_prompt_template": "Editorial product photography of {product_name} floating ethereally in center frame, dramatic single-source rim lighting from upper right, gradient background from deep teal #0d4a45 to lighter #187f77 with subtle golden particles suspended in air, hyperrealistic detail, shallow depth of field, Apple keynote product launch aesthetic, NO bowl, NO pet, NO hands, NO text on image, premium magazine quality, 1:1 ratio square format, ultra detailed, photorealistic NOT cartoon NOT illustration",
        "caption_template": "{product_hook}\n\n{product_specific_benefit}\n\n📦 {product_name} — ${product_price}\n🔗 bigotesypaticas.com/producto/{slug}\n📍 Mall Zamara Plaza, Local 2 · Dosquebradas\n\n#BigotesYPaticasPereira {category_hashtags}",
        "hashtags_pool": ["#AlimentoPerro", "#AlimentoGato", "#MascotasPereira", "#TiendaMascotas"],
        "cta_type": "product_link",
    },
    {
        "code": "awareness_adoption",
        "name": "Conciencia — Adopción",
        "category": "awareness",
        "visual_style": "documentary",
        "visual_prompt_template": "Documentary fine art photograph of mixed-breed adult dog profile silhouette against soft golden hour window light, contemplative mood, real not posed, mestizo not purebred, single paw print resting on weathered wood surface, muted earth tones with hints of teal in shadows, National Geographic emotional editorial style, single negative-space composition, NO direct eye contact with camera, NO smiling pet, NO cute cartoon, NO bowl, NO toys, photorealistic somber empathy, 1:1 ratio",
        "caption_template": "{adoption_hook}\n\n{specific_local_fact_about_animal_welfare_pereira_risaralda}\n\nEsta semana en Bigotes y Paticas estamos {action_offer}.\n\nSi estás pensando en adoptar, contactanos. Si no podés adoptar, podés apadrinar o donar alimento. Cualquier acción cuenta.\n\n📍 Mall Zamara Plaza · WhatsApp +57 320 687 6633\n\n#BigotesYPaticasPereira #AdopciónPereira #SegundaOportunidad #MascotasRisaralda",
        "hashtags_pool": ["#AdopciónPereira", "#SegundaOportunidad", "#MascotasRisaralda", "#TenenciaResponsable"],
        "cta_type": "awareness_action",
    },
    {
        "code": "review_typographic",
        "name": "Reseña — Tipográfica",
        "category": "review",
        "visual_style": "typographic",
        "visual_prompt_template": 'Editorial typography poster: large italic serif quotation "{review_quote_short}" rendered in deep teal #0d4a45 ink color on textured warm cream paper background, five hand-drawn golden ink stars #f5a641 below the quote, customer name "{customer_first_name}" and "Cliente verificado" in small sans-serif at bottom right, subtle golden paw print decoration in upper corner, Scandinavian minimalist poster aesthetic, centered balanced composition, fine paper texture grain visible, NO photos of people, NO icons of bowls or food, NO heart symbols, NO confetti, premium printed poster look, 1:1 ratio square',
        "caption_template": '{review_intro}\n\n"{review_quote_full}"\n— {customer_first_name}, {customer_location}\n\n{response_or_thank_you}\n\n¿Tu mascota tiene una historia con nosotros? Contanos abajo o dejanos tu reseña en Google — sumás 50 Puntos Bigotes para tu próxima compra.\n\n🔗 g.page/r/CfL67OgLB-10EBM/review\n\n#BigotesYPaticasPereira #ClientesReales #ReseñasVerificadas',
        "hashtags_pool": ["#ClientesReales", "#ReseñasVerificadas", "#MascotasPereira"],
        "cta_type": "portal_signup",
    },
    {
        "code": "educational_data",
        "name": "Educativo — Dato específico",
        "category": "educational",
        "visual_style": "editorial",
        "visual_prompt_template": 'Editorial infographic design: clean typographic composition centered on a specific data point "{key_data}", large display serif numbers in teal #187f77 contrasted with smaller technical sans-serif explanation in dark grey, textured cream background like artisan paper, single minimal vector illustration relevant to topic but conceptual geometric symbol NOT generic cute pet, golden accent line as visual divider, Kinfolk magazine editorial aesthetic, generous negative space, NO clipart, NO emoji-style icons, NO clichés, premium printed magazine quality, 1:1 ratio',
        "caption_template": "{educational_hook_specific_not_obvious}\n\n{technical_explanation_with_real_data}\n\n{specific_local_application_pereira}\n\n¿Tu mascota encaja en este caso? Pasá por la tienda y te asesoramos sin compromiso. Asesoría gratis con compra o sin ella.\n\n📍 Mall Zamara Plaza, Local 2\n💬 WhatsApp +57 320 687 6633\n\n#BigotesYPaticasPereira #CuidadoAnimal #VeterinariaPereira {topic_hashtags}",
        "hashtags_pool": ["#CuidadoAnimal", "#VeterinariaPereira", "#SaludMascotas", "#NutriciónAnimal"],
        "cta_type": "store_visit",
    },
    {
        "code": "reminder_service",
        "name": "Recordatorio Servicio",
        "category": "reminder",
        "visual_style": "typographic",
        "visual_prompt_template": "Minimalist editorial calendar visualization: large month grid layout with day {date_marker} highlighted by hand-drawn golden ink circle annotation, soft cream paper textured background, elegant serif typography for numbers, small illustrative dot motifs in teal as week markers, single decorative golden paw print in lower corner, Scandinavian design poster aesthetic, balanced asymmetric composition, premium printed magazine feel, NO cluttered icons, NO calendar app screenshots, NO cartoon mascots, NO photos of pets, 1:1 ratio",
        "caption_template": "{reminder_hook}\n\n{specific_timing_data_per_age_or_situation}\n\nEn Bigotes y Paticas trabajamos con {products_for_service}. Tenemos {specific_products_in_stock} disponibles esta semana.\n\n📅 Reservá tu turno por WhatsApp: +57 320 687 6633\n📍 Mall Zamara Plaza, Local 2 · L-S 10am-7pm\n\n#BigotesYPaticasPereira #SaludAnimal #CuidadoMascotas {service_hashtag}",
        "hashtags_pool": ["#SaludAnimal", "#CuidadoMascotas", "#VacunaciónPereira", "#BañoMascotas"],
        "cta_type": "whatsapp",
    },
    {
        "code": "sterilization_awareness",
        "name": "Conciencia — Esterilización",
        "category": "awareness",
        "visual_style": "documentary",
        "visual_prompt_template": "Conceptual editorial illustration: minimalist line drawing in single continuous golden ink stroke representing the cycle of life, soft cream textured background with subtle teal undertones, mathematical infographic showing exponential growth visualized abstractly with small geometric shapes radiating outward fractal pattern, premium National Geographic awareness campaign aesthetic, somber respectful mood, NO cute mascots, NO crying animals, NO blood or medical imagery, conceptual NOT literal, fine art editorial poster, 1:1 ratio",
        "caption_template": "{sterilization_hook}\n\nUna hembra sin esterilizar puede ser ancestro de {specific_calculation} descendientes en {timeframe}.\n\nEn Pereira y Dosquebradas hay jornadas de esterilización subsidiadas. {local_program_info}\n\nEsterilizar no es quitarle algo a tu mascota. Es darle salud, longevidad, y prevenir abandono futuro.\n\n📍 Asesoría gratis en Mall Zamara Plaza, Local 2\n💬 WhatsApp +57 320 687 6633\n\n#BigotesYPaticasPereira #EsterilizaciónResponsable #TenenciaResponsable #MascotasRisaralda",
        "hashtags_pool": ["#EsterilizaciónResponsable", "#TenenciaResponsable", "#MascotasRisaralda"],
        "cta_type": "awareness_action",
    },
    {
        "code": "local_pereira_pride",
        "name": "Identidad Local — Pereira",
        "category": "local",
        "visual_style": "editorial",
        "visual_prompt_template": "Fine art editorial landscape photograph: misty morning view of Pereira coffee hills in soft pastel light, distant silhouette of a single mestizo dog standing on a hilltop in middle distance very small in frame, atmospheric perspective with layered mountains fading into haze, golden hour or blue hour mood, subtle teal undertones in shadows, premium travel magazine cinematic aesthetic, NOT a portrait, NOT close-up of pet, the landscape is the primary subject, contemplative wide composition, soft vignette, 1:1 ratio",
        "caption_template": "{local_hook}\n\n{local_specific_data_or_story_pereira_dosquebradas}\n\nSomos de aquí. Conocemos el clima, las rutas, las necesidades específicas de las mascotas en el Eje Cafetero. Por eso seleccionamos productos que realmente funcionen acá.\n\n📍 Mall Zamara Plaza, Local 2 — Dosquebradas\n🌐 bigotesypaticas.com\n\n#BigotesYPaticasPereira #PereiraColombia #Dosquebradas #EjeCafetero #MascotasRisaralda",
        "hashtags_pool": ["#PereiraColombia", "#Dosquebradas", "#EjeCafetero", "#MascotasRisaralda"],
        "cta_type": "store_visit",
    },
    {
        "code": "meme_smart",
        "name": "Meme — Humor inteligente",
        "category": "meme",
        "visual_style": "editorial",
        "visual_prompt_template": 'Wes Anderson inspired symmetrical composition: a single object related to "{meme_topic}" centered in frame, pastel color palette with brand teal #187f77 and golden #f5a641 accents, vintage retro-modern aesthetic, deadpan visual humor through composition not through cartoon elements, clean minimalist arrangement, soft diffused lighting, premium editorial look like Wes Anderson film still, NO speech bubbles, NO cartoon expressions, NO Comic Sans, NO standard meme template, conceptual humor through visual elements only, 1:1 ratio',
        "caption_template": "{meme_caption_short_observation}\n\n{punchline_or_witty_observation}\n\n#BigotesYPaticasPereira #HumorMascotero #VidaConMascotas",
        "hashtags_pool": ["#HumorMascotero", "#VidaConMascotas", "#MascotasPereira"],
        "cta_type": None,
    },
    {
        "code": "product_with_purpose",
        "name": "Producto + Causa",
        "category": "product",
        "visual_style": "editorial",
        "visual_prompt_template": "Editorial still life composition: {product_name} positioned alongside an abstract symbol of the cause it serves (small empty bowl casting shadow for 'share food' cause, or seed for sustainability), warm natural light from window, textured linen background in cream tones, subtle teal accent in single element, documentary photography aesthetic mixed with editorial product staging, contemplative storytelling mood, NO live animals, NO smiling pet faces, NO direct sales pitch visuals, premium social impact campaign feel, 1:1 ratio",
        "caption_template": "{purpose_hook}\n\nPor cada {product_name} que vendemos esta semana, donamos {donation_amount} en alimento a {beneficiary_organization}.\n\n{product_specific_value}\n\n📦 {product_name} — ${product_price}\n🔗 bigotesypaticas.com/producto/{slug}\n\nTu compra alimenta dos historias.\n\n#BigotesYPaticasPereira #ConsumoConsciente #CausaAnimal",
        "hashtags_pool": ["#ConsumoConsciente", "#CausaAnimal", "#MascotasPereira"],
        "cta_type": "product_link",
    },
    {
        "code": "before_after_real",
        "name": "Transformación Real",
        "category": "awareness",
        "visual_style": "documentary",
        "visual_prompt_template": "Diptych split-frame composition: left side empty weathered dog bowl on concrete floor in cold morning light, right side same setting same bowl but full with warm food in warmer golden afternoon light, narrative sequential storytelling through environmental change, documentary emotional realism, no animals visible in frame, the absence and presence tells the story, fine art photography aesthetic, muted earth tones with brand teal in shadows, balanced diptych composition, 1:1 ratio total square",
        "caption_template": "{transformation_hook}\n\n{specific_real_story_or_data_local}\n\nCada animal que adopta una familia tiene una historia anterior. Cada mascota bien alimentada tuvo días sin comer. Cada esterilización previene camadas no deseadas.\n\nHacé tu parte. Adoptá. Esterilizá. Educá.\n\n📍 Mall Zamara Plaza, Local 2\n💬 WhatsApp +57 320 687 6633\n\n#BigotesYPaticasPereira #SegundaVida #TenenciaResponsable",
        "hashtags_pool": ["#SegundaVida", "#TenenciaResponsable", "#AdopciónPereira"],
        "cta_type": "awareness_action",
    },
    {
        "code": "portal_promotion",
        "name": "Portal Autogestión",
        "category": "product",
        "visual_style": "apple_minimal",
        "visual_prompt_template": "Editorial flat-lay composition: a single elegant smartphone displayed floating diagonally in frame showing abstract minimal interface elements NOT a real app screenshot, surrounded by floating geometric shapes representing brand teal #187f77 and golden #f5a641, premium hyperrealistic product photography style, dramatic rim lighting, deep shadow gradient background fading from dark teal to lighter teal, Apple keynote aesthetic, NO actual UI text visible, NO logos visible on screen, NO pet images, abstract concept of digital experience, 1:1 ratio",
        "caption_template": "{portal_hook}\n\nEn el portal de Bigotes y Paticas podés:\n✓ Ganar Puntos Bigotes con cada compra\n✓ Llevar el historial médico y de productos de tu mascota\n✓ Pedir productos sin moverte de casa\n✓ Reservar servicios (baño, vacunación)\n✓ Reseñar productos y ganar más puntos\n\nEs gratis y tarda 30 segundos crearte cuenta.\n\n🔗 mi.bigotesypaticas.com\n📱 Instalalo como app desde el navegador\n\n#BigotesYPaticasPereira #TecnologíaParaMascotas #PuntosBigotes",
        "hashtags_pool": ["#TecnologíaParaMascotas", "#PuntosBigotes", "#PortalBigotes"],
        "cta_type": "portal_signup",
    },
    {
        "code": "expert_tip",
        "name": "Consejo Experto",
        "category": "educational",
        "visual_style": "editorial",
        "visual_prompt_template": "Editorial fine art photograph: a single relevant object such as veterinary stethoscope, weathered book of veterinary medicine, ceramic measuring spoon, or hourglass, centered in frame on textured cream paper or natural linen background, dramatic side-lighting creating long soft shadows, golden hour mood with brand teal accents in shadows, Kinfolk magazine photography style, contemplative authority aesthetic, NO live animals in frame, NO product packaging visible, conceptual object metaphor for the tip topic, 1:1 ratio",
        "caption_template": "{expert_hook_not_obvious}\n\n{specific_technical_tip_with_data}\n\n{common_misconception_corrected}\n\nSi tenés dudas específicas sobre tu mascota, pasá por la tienda. Asesoramos gratis, sea que compres o no.\n\n📍 Mall Zamara Plaza, Local 2 · L-S 10am-7pm\n\n#BigotesYPaticasPereira #ConsejoExperto #CuidadoAnimal {topic_hashtags}",
        "hashtags_pool": ["#ConsejoExperto", "#CuidadoAnimal", "#SaludMascotas"],
        "cta_type": "store_visit",
    },
]


def seed(reset: bool = False) -> None:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    if reset:
        cur.execute("DELETE FROM content.post_templates")
        print("  ⚠️  Templates existentes eliminados (--reset)")

    inserted = updated = 0
    for t in TEMPLATES:
        cur.execute("""
            INSERT INTO content.post_templates
                (code, name, category, visual_style, visual_prompt_template,
                 caption_template, hashtags_pool, cta_type, active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true)
            ON CONFLICT (code) DO UPDATE SET
                name                   = EXCLUDED.name,
                category               = EXCLUDED.category,
                visual_style           = EXCLUDED.visual_style,
                visual_prompt_template = EXCLUDED.visual_prompt_template,
                caption_template       = EXCLUDED.caption_template,
                hashtags_pool          = EXCLUDED.hashtags_pool,
                cta_type               = EXCLUDED.cta_type
            RETURNING (xmax = 0) AS is_insert
        """, (
            t["code"], t["name"], t["category"], t["visual_style"],
            t["visual_prompt_template"], t["caption_template"],
            t.get("hashtags_pool", []), t.get("cta_type"),
        ))
        row = cur.fetchone()
        if row and row[0]:
            inserted += 1
        else:
            updated += 1

    conn.commit()

    cur.execute("""
        SELECT category, COUNT(*) FROM content.post_templates GROUP BY category ORDER BY category
    """)
    print("\n✅ Templates en DB por categoría:")
    total = 0
    for cat, cnt in cur.fetchall():
        print(f"   {cat:<20} {cnt}")
        total += cnt
    print(f"   {'TOTAL':<20} {total}")

    print(f"\n   Insertados: {inserted} · Actualizados: {updated}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true", help="Eliminar todos antes de re-insertar")
    args = p.parse_args()
    seed(reset=args.reset)
