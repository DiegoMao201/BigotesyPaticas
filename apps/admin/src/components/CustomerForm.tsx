'use client';

import { useBorrador } from '@/lib/borradores';
import { BorradorAviso } from '@/components/BorradorAviso';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DialogBody, DialogFooter } from '@/components/ui/dialog';
import { type Customer } from '@/lib/api';
import { PHONE_COUNTRIES, parsePhoneForForm, composePhone } from '@/lib/phone';

export type CustomerFormData = {
  full_name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  document_id: string;
  pet_name: string;
  pet_type: string;
  pet_notes: string;
  pet_birthday: string;
  last_deworming: string;
  notes: string;
};

/** Formulario de cliente (Clientes y el botón "Cliente nuevo" del POS). Lo escrito se
 *  guarda como borrador bajo `prefijo` (lib/borradores.ts): crear desde el POS no pisa
 *  lo que se lleve a medias en Clientes. `initial` sin id = datos sugeridos de un cliente nuevo. */
export function CustomerForm({
  initial,
  onSubmit,
  loading,
  prefijo = 'clientes',
}: {
  initial?: Partial<Customer>;
  onSubmit: (d: CustomerFormData) => void;
  loading: boolean;
  prefijo?: string;
}) {
  const clave = initial?.id ? `${prefijo}:form:${initial.id}` : `${prefijo}:nuevo:form`;
  const [form, setForm] = useBorrador<CustomerFormData>(clave, {
    full_name: initial?.full_name || '',
    email: initial?.email || '',
    phone: initial?.phone || '',
    address: initial?.address || '',
    city: initial?.city || '',
    document_id: initial?.document_id || '',
    pet_name: initial?.pet_name || '',
    pet_type: initial?.pet_type || '',
    pet_notes: initial?.pet_notes || '',
    pet_birthday: initial?.pet_birthday || '',
    last_deworming: initial?.last_deworming || '',
    notes: initial?.notes || '',
  });
  const set = (k: keyof CustomerFormData, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const parsedInitialPhone = parsePhoneForForm(initial?.phone);
  const [phoneDial, setPhoneDial] = useBorrador(`${clave}:indicativo`, parsedInitialPhone.dial);
  const [phoneLocal, setPhoneLocal] = useBorrador(`${clave}:celular`, parsedInitialPhone.local);
  function updatePhone(dial: string, local: string) {
    setPhoneDial(dial);
    setPhoneLocal(local);
    set('phone', composePhone(dial, local));
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
    >
      <DialogBody className="space-y-3">
        <BorradorAviso prefijo={clave} />
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs font-medium mb-1 block">Nombre completo *</label>
            <Input required value={form.full_name} onChange={(e) => set('full_name', e.target.value)} placeholder="Juan García" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Email</label>
            <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="email@ejemplo.com" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Teléfono (WhatsApp)</label>
            <div className="flex gap-1.5">
              <select
                className="w-[88px] shrink-0 rounded-md border border-input bg-background px-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={phoneDial}
                onChange={(e) => updatePhone(e.target.value, phoneLocal)}
                aria-label="Código de país"
              >
                {PHONE_COUNTRIES.map((c) => (
                  <option key={`${c.dial}-${c.name}`} value={c.dial}>{c.flag} +{c.dial}</option>
                ))}
              </select>
              <Input
                value={phoneLocal}
                onChange={(e) => updatePhone(phoneDial, e.target.value)}
                placeholder={phoneDial === '57' ? '300 000 0000' : 'Número local'}
                className="flex-1"
              />
            </div>
            {phoneDial !== '57' && (
              <p className="mt-1 text-[11px] font-medium text-amber-700">
                Ojo: indicativo +{phoneDial} ({PHONE_COUNTRIES.find((c) => c.dial === phoneDial)?.name ?? 'otro país'}), no Colombia.
              </p>
            )}
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Ciudad</label>
            <Input value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="Dosquebradas" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Dirección</label>
            <Input value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="Cra 10 # 20-30" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Documento (CC/NIT)</label>
            <Input value={form.document_id} onChange={(e) => set('document_id', e.target.value)} placeholder="1234567890" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Mascota (nombre)</label>
            <Input value={form.pet_name} onChange={(e) => set('pet_name', e.target.value)} placeholder="Luna" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Tipo de mascota</label>
            <Input value={form.pet_type} onChange={(e) => set('pet_type', e.target.value)} placeholder="Perro / Gato" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Cumpleaños mascota</label>
            <Input type="date" value={form.pet_birthday} onChange={(e) => set('pet_birthday', e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Última desparasitación</label>
            <Input type="date" value={form.last_deworming} onChange={(e) => set('last_deworming', e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium mb-1 block">Notas de mascota</label>
            <Input value={form.pet_notes} onChange={(e) => set('pet_notes', e.target.value)} placeholder="Raza, edad, alergias..." />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium mb-1 block">Notas</label>
            <textarea
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              rows={2}
              placeholder="Notas internas…"
              className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={loading || !form.full_name}>
          {loading ? 'Guardando…' : initial?.id ? 'Guardar cambios' : 'Crear cliente'}
        </Button>
      </DialogFooter>
    </form>
  );
}

/** Lo que espera la API: los campos vacíos no se mandan. */
export function aPayload(d: CustomerFormData) {
  return {
    ...d,
    email: d.email || undefined,
    phone: d.phone || undefined,
    address: d.address || undefined,
    city: d.city || undefined,
    document_id: d.document_id || undefined,
    pet_name: d.pet_name || undefined,
    pet_type: d.pet_type || undefined,
    pet_notes: d.pet_notes || undefined,
    pet_birthday: d.pet_birthday || undefined,
    last_deworming: d.last_deworming || undefined,
    notes: d.notes || undefined,
  };
}
