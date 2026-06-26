'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import {
  ArrowLeft, Download, Plus, AlertCircle,
  CheckCircle, Clock, ChevronDown, ChevronUp
} from 'lucide-react';
import { pets, type HealthRecord } from '@/lib/api';
import { PET_THEME_COLORS } from '@/lib/pet-store';
import { getSpeciesEmoji, formatDate, formatRelativeDate, cn } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { PetPhotoUploader } from '@/components/portal/PetPhotoUploader';

export default function PetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: pet, isLoading } = useQuery({
    queryKey: ['portal-pet', id],
    queryFn: () => pets.get(id),
  });

  const [showAddHealth, setShowAddHealth] = useState(false);
  const [healthForm, setHealthForm] = useState({
    record_type: 'vacuna',
    name: '',
    applied_at: new Date().toISOString().split('T')[0],
    next_due_at: '',
    vet_name: '',
    notes: '',
  });

  const { mutate: addRecord, isPending } = useMutation({
    mutationFn: (data: typeof healthForm) =>
      pets.addHealthRecord(id, {
        ...data,
        next_due_at: data.next_due_at || null,
        vet_name: data.vet_name || null,
        notes: data.notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portal-pet', id] });
      qc.invalidateQueries({ queryKey: ['portal-pets'] });
      toast.success('Registro guardado');
      setShowAddHealth(false);
      setHealthForm({
        record_type: 'vacuna', name: '',
        applied_at: new Date().toISOString().split('T')[0],
        next_due_at: '', vet_name: '', notes: '',
      });
    },
    onError: (err: any) => toast.error(err.message),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!pet) return <p className="p-6 text-muted">Mascota no encontrada.</p>;

  const theme = PET_THEME_COLORS[pet.color_theme];

  return (
    <div data-pet-theme={pet.color_theme} className="flex flex-col">
      {/* Header con color de mascota */}
      <div className="p-4 pt-6 pb-6" style={{ backgroundColor: theme.primary }}>
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-xl bg-white/20 text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-display text-xl font-bold text-white">{pet.name}</h1>
          <a
            href={pets.carnetUrl(pet.id)}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto p-2 rounded-xl bg-white/20 text-white"
            title="Descargar carnet PDF"
          >
            <Download className="h-5 w-5" />
          </a>
        </div>

        <div className="flex items-center gap-4">
          {/* Avatar: foto real o emoji */}
          <div className="h-20 w-20 rounded-2xl bg-white/20 flex items-center justify-center text-4xl shrink-0 overflow-hidden">
            {pet.photo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={pet.photo_url}
                alt={`Foto de ${pet.name}`}
                className="h-full w-full object-cover"
              />
            ) : (
              <span>{getSpeciesEmoji(pet.species)}</span>
            )}
          </div>
          <div className="text-white flex-1 min-w-0">
            <p className="text-white/80 text-sm capitalize">
              {pet.species}{pet.breed ? ` • ${pet.breed}` : ''}
            </p>
            {pet.age_years != null && (
              <p className="font-semibold">
                {pet.age_years} año{pet.age_years !== 1 ? 's' : ''}
                {pet.age_months ? ` y ${pet.age_months} mes${pet.age_months !== 1 ? 'es' : ''}` : ''}
              </p>
            )}
            {pet.weight_kg && <p className="text-white/80 text-sm">{pet.weight_kg} kg</p>}
            {pet.food_brand && (
              <p className="text-white/80 text-sm">🍖 {pet.food_brand}</p>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 flex flex-col gap-5">
        {/* Foto de mascota */}
        <div>
          <h2 className="font-display font-bold text-foreground mb-3">Foto de {pet.name}</h2>
          <PetPhotoUploader
            petId={pet.id}
            currentPhotoUrl={pet.photo_url}
            petName={pet.name}
            accentColor={theme.primary}
          />
        </div>

        {/* Registro de salud */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display font-bold text-foreground">Historial de salud</h2>
            <button
              onClick={() => setShowAddHealth(!showAddHealth)}
              className="flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-xl"
              style={{ backgroundColor: theme.light, color: theme.dark }}
            >
              <Plus className="h-3.5 w-3.5" />
              Agregar
              {showAddHealth ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          </div>

          {/* Formulario add registro */}
          {showAddHealth && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="card mb-4 flex flex-col gap-3 border-2"
              style={{ borderColor: theme.primary }}
            >
              <select
                className="input-field"
                value={healthForm.record_type}
                onChange={(e) => setHealthForm((f) => ({ ...f, record_type: e.target.value }))}
              >
                <option value="vacuna">Vacuna</option>
                <option value="desparasitacion">Desparasitación</option>
                <option value="consulta">Consulta veterinaria</option>
                <option value="cirugia">Cirugía</option>
                <option value="otro">Otro</option>
              </select>
              <input
                className="input-field"
                placeholder="Nombre / descripción *"
                value={healthForm.name}
                onChange={(e) => setHealthForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-muted mb-1 block">Fecha aplicación</label>
                  <input
                    type="date"
                    className="input-field"
                    value={healthForm.applied_at}
                    onChange={(e) => setHealthForm((f) => ({ ...f, applied_at: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1 block">Próxima dosis</label>
                  <input
                    type="date"
                    className="input-field"
                    value={healthForm.next_due_at}
                    onChange={(e) => setHealthForm((f) => ({ ...f, next_due_at: e.target.value }))}
                  />
                </div>
              </div>
              <input
                className="input-field"
                placeholder="Veterinario"
                value={healthForm.vet_name}
                onChange={(e) => setHealthForm((f) => ({ ...f, vet_name: e.target.value }))}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddHealth(false)}
                  className="btn-outline flex-1"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={isPending || !healthForm.name}
                  onClick={() => addRecord(healthForm)}
                  className="btn-primary flex-1"
                  style={{ backgroundColor: theme.primary }}
                >
                  {isPending ? '...' : 'Guardar'}
                </button>
              </div>
            </motion.div>
          )}

          {/* Lista registros */}
          {pet.health_records.length === 0 ? (
            <p className="text-muted text-sm text-center py-6">
              Sin registros de salud aún. ¡Agrega vacunas y desparasitaciones!
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {pet.health_records.map((hr) => (
                <HealthRecordCard key={hr.id} record={hr} theme={theme} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthRecordCard({
  record,
  theme,
}: {
  record: HealthRecord;
  theme: { primary: string; light: string; dark: string };
}) {
  const alertIcon =
    record.alert_level === 'overdue' ? (
      <AlertCircle className="h-4 w-4 text-red-500" />
    ) : record.alert_level === 'soon' ? (
      <Clock className="h-4 w-4 text-amber-500" />
    ) : record.next_due_at ? (
      <CheckCircle className="h-4 w-4 text-green-500" />
    ) : null;

  const RECORD_ICONS: Record<string, string> = {
    vacuna: '💉',
    desparasitacion: '🪱',
    consulta: '🩺',
    cirugia: '🏥',
    otro: '📋',
  };

  return (
    <div className="card py-3 flex items-start gap-3">
      <div
        className="h-9 w-9 rounded-xl flex items-center justify-center text-lg shrink-0"
        style={{ backgroundColor: theme.light }}
      >
        {RECORD_ICONS[record.record_type] ?? '📋'}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground">{record.name}</p>
        <p className="text-xs text-muted">
          {formatDate(record.applied_at)}
          {record.vet_name ? ` • Dr/a. ${record.vet_name}` : ''}
        </p>
        {record.next_due_at && (
          <p className="text-xs mt-0.5" style={{ color: record.alert_level === 'overdue' ? '#dc2626' : record.alert_level === 'soon' ? '#d97706' : '#16a34a' }}>
            Próx. dosis: {formatRelativeDate(record.next_due_at)}
          </p>
        )}
      </div>
      {alertIcon}
    </div>
  );
}
