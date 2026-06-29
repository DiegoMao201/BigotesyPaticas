/** Fuente única de verdad para datos del negocio — usada en todos los schemas JSON-LD. */
export const BUSINESS_INFO = {
  name: "Bigotes y Paticas",
  legalName: "Diego Mauricio García — Bigotes y Paticas",
  alternateName: "Bigotes y Paticas Dosquebradas",
  alternateNames: [
    "Pet Shop Pereira",
    "Pet Shop Dosquebradas",
    "Petshop Pereira",
    "Petshop Dosquebradas",
  ],
  description:
    "Pet shop y tienda de mascotas en Pereira y Dosquebradas. Concentrados, accesorios, medicamentos veterinarios con domicilio en 24-72h. El mejor pet shop con domicilio en Risaralda.",
  url: "https://bigotesypaticas.com",
  logo: "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png",

  phone: "+573206876633",
  phoneDisplay: "320 687 6633",
  whatsapp: "573206876633",
  email: "bigotesypaticasdosquebradas@gmail.com",

  address: {
    streetAddress: "Mall Zamara Plaza, Cl. 15 #3A-07 Local 2",
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

  priceRange: "$$",
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
    standardShippingCost: 8000,
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

  // Completar con URL del perfil real cuando Diego confirme el CID
  mapsUrl:
    "https://www.google.com/maps/search/?api=1&query=Bigotes+y+Paticas+Dosquebradas",

  // Agregar cuando se activen redes sociales
  sameAs: [] as string[],

  legal: {
    nit: "1088266407",
    nitFormatted: "NIT 1088266407-7",
    owner: "Diego Mauricio García",
    regime: "Régimen Simple de Tributación",
    dataProtectionLaw: "Ley 1581 de 2012",
    privacyEmail: "bigotesypaticasdosquebradas@gmail.com",
  },
} as const;
