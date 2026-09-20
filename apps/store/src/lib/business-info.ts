/** Fuente única de verdad para datos del negocio — usada en todos los schemas JSON-LD. */
export const BUSINESS_INFO = {
  // EXACTAMENTE el nombre de la ficha de Google (Perfil de Empresa, cambio
  // aprobado el 18-sep-2026). Google consolida web y ficha como la misma entidad
  // solo si el nombre coincide letra por letra; con "Bigotes y Paticas" a secas
  // en el JSON-LD y en el mapa, la web y la ficha se leían como dos negocios.
  name: "Bigotes y Paticas Tienda de Mascotas",
  legalName: "Diego Mauricio García — Bigotes y Paticas",
  alternateName: "Bigotes y Paticas",
  alternateNames: [
    "Bigotes y Paticas Dosquebradas",
    "Pet Shop Pereira",
    "Pet Shop Dosquebradas",
    "Petshop Pereira",
    "Petshop Dosquebradas",
  ],
  description:
    "Pet shop y tienda de mascotas en Pereira y Dosquebradas. Concentrados, accesorios, medicamentos veterinarios con domicilio el mismo día. El mejor pet shop con domicilio en Risaralda.",
  url: "https://bigotesypaticas.com",
  logo: "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png",

  phone: "+573206876633",
  phoneDisplay: "320 687 6633",
  whatsapp: "573206876633",
  email: "bigotesypaticasdosquebradas@gmail.com",

  address: {
    streetAddress: "Samara Plaza Mall, Cl. 15 #3A-07 Local 2",
    addressLocality: "Dosquebradas",
    addressRegion: "Risaralda",
    postalCode: "661001",
    addressCountry: "CO",
  },

  geo: {
    latitude: 4.827259,
    longitude: -75.692291,
  },

  openingHours: [
    {
      days: [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ],
      opens: "10:00",
      closes: "19:00",
    },
  ],

  areaServed: ["Pereira", "Dosquebradas"],

  // Servicios en tienda, confirmados por Diego el 8 sep 2026 (los mismos que declara la pagina de Facebook)
  services: [
    { name: "Grooming", description: "Baño y peluquería completos para perros y gatos" },
    { name: "Consulta veterinaria", description: "Consulta veterinaria en tienda" },
    { name: "Vacunación con carnet", description: "Vacunación con registro en carnet" },
  ],

  priceRange: "$$$",  // marcas premium; igual que la pagina de Facebook (8 sep 2026)
  currenciesAccepted: "COP",
  paymentMethods: [
    "Cash",
    "Credit Card",
    "Debit Card",
    "Bank Transfer",
    "Nequi",
    "Daviplata",
  ],

  rating: {
    value: "5.0",
    reviewCount: 6,
    bestRating: 5,
  },

  features: {
    wheelchairAccessibleEntrance: true,
    homeDelivery: true,
    womanOwned: true,
    curbsidePickup: true,
    inStorePickup: true,
  },

  shipping: {
    freeShippingMinimum: 30000,
    standardShippingCost: 3000,
    transitDaysMin: 1,
    transitDaysMax: 3,
    handlingDaysMin: 0,
    handlingDaysMax: 1,
  },

  returns: {
    window: 30,
    method: "ReturnByMail",
    fees: "FreeReturn",
    country: "CO",
  },

  // Confirmado el 13-sep-2026 con la API de Places: la ficha existe, está
  // OPERATIONAL, categoría pet_store, 5,0 con 28 reseñas. Este es su enlace
  // canónico por cid; antes había una búsqueda por texto, que no apunta a la ficha.
  mapsUrl: "https://maps.google.com/?cid=8425398225613945586",

  // Redes verificadas (no inventar): Instagram y TikTok por nombre de usuario real;
  // Facebook por nombre de usuario (BigotesyPaticas, creado el 8 sep 2026; antes solo por id).
  // YouTube: canal UC3kyMQMz10R3jdmgscZ5H7Q con el mismo @usuario, creado el 11 sep 2026.
  social: {
    instagram: { url: "https://www.instagram.com/bigotesypaticas/", handle: "@bigotesypaticas" },
    tiktok: { url: "https://www.tiktok.com/@bigotesypaticas", handle: "@bigotesypaticas" },
    facebook: { url: "https://www.facebook.com/BigotesyPaticas", handle: "/BigotesyPaticas" },
    youtube: { url: "https://www.youtube.com/@bigotesypaticas", handle: "@bigotesypaticas" },
    whatsapp: { url: "https://wa.me/573206876633", handle: "320 687 6633" },
    googleReviews: { url: "https://g.page/r/CfL67OgLB-10EBM/review", handle: "Google" },
  },

  // La ficha del negocio en Google, por su identificador propio. Ponerla aquí y en
  // hasMap le dice a Google que esta web y ese punto del mapa son la MISMA entidad.
  // Un enlace de búsqueda por texto no sirve: apunta a lo que Google encuentre,
  // no a la ficha. Place ID ChIJUbZRoXGBOI4R8vrs6AsH7XQ.
  googleBusinessUrl: "https://maps.google.com/?cid=8425398225613945586",

  sameAs: [
    "https://maps.google.com/?cid=8425398225613945586",
    "https://www.instagram.com/bigotesypaticas/",
    "https://www.tiktok.com/@bigotesypaticas",
    "https://www.facebook.com/BigotesyPaticas",
    "https://www.youtube.com/@bigotesypaticas",
  ] as string[],

  legal: {
    nit: "1088266407",
    nitFormatted: "NIT 1088266407-7",
    owner: "Diego Mauricio García",
    regime: "Régimen Simple de Tributación",
    dataProtectionLaw: "Ley 1581 de 2012",
    privacyEmail: "bigotesypaticasdosquebradas@gmail.com",
  },
} as const;
