'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Plus, ChevronRight, AlertCircle, Download } from 'lucide-react';
import { pets } from '@/lib/api';
import { PET_THEME_COLORS } from '@/lib/pet-store';
import { getSpeciesEmoji } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

import { Logo } from '@/components/brand/Logo';

export default function PetsPage() {
  const { data: petsData, isLoading } = useQuery({
    queryKey: ['portal-pets'],
    queryFn: pets.list,
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-foreground">Mis mascotas</h1>
        <Link href="/pets/new" className="btn-primary py-2 px-4 text-xs">
          <Plus className="h-4 w-4" /> Nueva
        </Link>
      </div>

      {petsData?.length === 0 && (
        <div className="card flex flex-col items-center gap-4 py-12 text-center">
          <Logo size={80} />
          <p className="font-semibold text-foreground">Aún no tienes mascotas registradas</p>
          <Link href="/pets/new" className="btn-primary">Registrar mascota</Link>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {petsData?.map((pet, i) => {
          const theme = PET_THEME_COLORS[pet.color_theme];
          const overdueAlerts = pet.health_records.filter((r) => r.alert_level === 'overdue');
          const soonAlerts = pet.health_records.filter((r) => r.alert_level === 'soon');

          return (
            <motion.div
              key={pet.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link href={`/pets/${pet.id}`} className="card flex items-center gap-4 py-4 hover:shadow-card-hover transition-shadow">
                <div
                  className="h-14 w-14 rounded-2xl flex items-center justify-center text-2xl shrink-0"
                  style={{ backgroundColor: theme.light }}
                >
                  {getSpeciesEmoji(pet.species)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-display font-bold text-foreground">{pet.name}</p>
                    {overdueAlerts.length > 0 && (
                      <span className="flex items-center gap-0.5 text-xs text-red-600 font-semibold">
                        <AlertCircle className="h-3 w-3" />
                        {overdueAlerts.length} vencida{overdueAlerts.length > 1 ? 's' : ''}
                      </span>
                    )}
                    {soonAlerts.length > 0 && overdueAlerts.length === 0 && (
                      <span className="text-xs text-amber-600 font-semibold">
                        {soonAlerts.length} próxima{soonAlerts.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted capitalize">
                    {pet.species}
                    {pet.breed ? ` • ${pet.breed}` : ''}
                    {pet.age_years != null ? ` • ${pet.age_years} año${pet.age_years !== 1 ? 's' : ''}` : ''}
                  </p>
                  {pet.food_brand && (
                    <p className="text-xs text-muted mt-0.5">🍖 {pet.food_brand}</p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={pets.carnetUrl(pet.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    title="Descargar carnet PDF"
                    className="p-2 rounded-xl hover:bg-gray-100 transition-colors"
                    style={{ color: theme.primary }}
                  >
                    <Download className="h-4 w-4" />
                  </a>
                  <ChevronRight className="h-5 w-5 text-muted" />
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
