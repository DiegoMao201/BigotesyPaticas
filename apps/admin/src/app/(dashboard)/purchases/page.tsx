'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingCart, Upload, FileText, Plus, Trash2, Search, Save, Eye, Truck, Sparkles,
  AlertTriangle, CheckCircle2, Package, X, FileUp, Edit2, RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  purchases, suppliers as suppliersApi, products as productsApi, adminEtl,
  type ParsedInvoice, type ParsedItem, type Supplier, type SupplierIn,
  type PurchaseSummary,
} from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Pagination } from '@/components/ui/pagination';

type Tab = 'historial' | 'nueva-xml' | 'nueva-manual';
type Step = 1 | 2 | 3;

interface EditableItem extends ParsedItem {
  _id: string;
  factor_pack: number;
  margen_pct: number;
}

const DEFAULT_MARGIN = 20;

export default function PurchasesPage() {
  const [tab, setTab] = useState<Tab>('historial');
  const qc = useQueryClient();
  const bootstrapMut = useMutation({
    mutationFn: () => adminEtl.bootstrapSuppliers(),
    onSuccess: (res) => {
      toast.success(`Proveedores creados: ${res.created} nuevos, ${res.skipped} ya existían`);
      qc.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (e: Error) => toast.error(`Error: ${e.message}`),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <ShoppingCart className="h-8 w-8 text-orange-500" />
            Compras a Proveedores
          </h1>
          <p className="text-gray-600 mt-1">Carga facturas DIAN, asocia productos y genera órdenes</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => bootstrapMut.mutate()}
          disabled={bootstrapMut.isPending}
          className="text-orange-600 border-orange-300 hover:bg-orange-50"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          {bootstrapMut.isPending ? 'Importando…' : 'Importar proveedores legados'}
        </Button>
      </div>

      <div className="flex gap-2 border-b">
        {[
          { id: 'historial', label: 'Historial', icon: FileText },
          { id: 'nueva-xml', label: 'Nueva con XML DIAN', icon: FileUp },
          { id: 'nueva-manual', label: 'Nueva manual', icon: Edit2 },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as Tab)}
            className={`px-4 py-2 font-medium border-b-2 transition flex items-center gap-2 ${
              tab === t.id ? 'border-orange-500 text-orange-600' : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <t.icon className="h-4 w-4" />{t.label}
          </button>
        ))}
      </div>

      {tab === 'historial' && <HistorialTab />}
      {tab === 'nueva-xml' && <NuevaXmlTab onDone={() => setTab('historial')} />}
      {tab === 'nueva-manual' && <NuevaManualTab onDone={() => setTab('historial')} />}
    </div>
  );
}

// ─── HISTORIAL ────────────────────────────────────────────────────
function HistorialTab() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [viewing, setViewing] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['purchases', search, page],
    queryFn: () => purchases.list({ q: search || undefined, page, page_size: 20 }),
  });

  const stats = useQuery({ queryKey: ['purchases-stats'], queryFn: () => purchases.stats() });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Gasto del mes</p>
          <p className="text-2xl font-bold">{formatCurrency(stats.data?.total_spend_month || 0)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Compras del mes</p>
          <p className="text-2xl font-bold">{stats.data?.total_count_month || 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Top proveedor</p>
          <p className="text-lg font-bold truncate">{stats.data?.top_suppliers?.[0]?.supplier_name || '—'}</p>
        </Card>
      </div>

      <Card className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por folio o proveedor..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-10"
          />
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">Cargando...</div>
        ) : !data?.items.length ? (
          <div className="p-12 text-center text-gray-500">No hay compras registradas</div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Fecha</th>
                  <th className="text-left p-3">Folio</th>
                  <th className="text-left p-3">Proveedor</th>
                  <th className="text-right p-3">Items</th>
                  <th className="text-right p-3">Total</th>
                  <th className="text-center p-3">Estado</th>
                  <th className="text-center p-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p: PurchaseSummary) => (
                  <tr key={p.id} className="border-t hover:bg-gray-50">
                    <td className="p-3">{new Date(p.purchased_at).toLocaleDateString('es-CO')}</td>
                    <td className="p-3 font-mono text-xs">{p.folio || '—'}</td>
                    <td className="p-3">{p.supplier_name}</td>
                    <td className="p-3 text-right">{p.items_count}</td>
                    <td className="p-3 text-right font-bold">{formatCurrency(p.total)}</td>
                    <td className="p-3 text-center">
                      <Badge className={
                        p.status === 'received' ? 'bg-green-100 text-green-700' :
                        p.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }>{p.status}</Badge>
                    </td>
                    <td className="p-3 text-center">
                      <Button size="sm" variant="outline" onClick={() => setViewing(p.id)}>
                        <Eye className="h-3 w-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {data && data.total > data.page_size && (
        <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
      )}

      {viewing && <PurchaseDetailDialog id={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

function PurchaseDetailDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const { data, isLoading } = useQuery({ queryKey: ['purchase', id], queryFn: () => purchases.get(id) });
  return (
    <Dialog open onClose={onClose} title={data ? `Compra ${data.folio || data.id.slice(0, 8)}` : 'Compra'} size="lg">
      <DialogBody>
        {isLoading ? (
          <div className="text-center py-8">Cargando...</div>
        ) : data ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Proveedor:</span> <strong>{data.supplier_name}</strong></div>
              <div><span className="text-gray-500">Fecha:</span> {new Date(data.purchased_at).toLocaleDateString('es-CO')}</div>
              <div><span className="text-gray-500">Estado:</span> {data.status}</div>
              <div><span className="text-gray-500">Pago:</span> {data.payment_method}</div>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">Producto</th>
                  <th className="text-right p-2">Cant</th>
                  <th className="text-right p-2">Costo</th>
                  <th className="text-right p-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t">
                    <td className="p-2">{it.product_name}</td>
                    <td className="p-2 text-right">{it.quantity}</td>
                    <td className="p-2 text-right">{formatCurrency(it.unit_cost)}</td>
                    <td className="p-2 text-right font-bold">{formatCurrency(it.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t font-bold">
                  <td colSpan={3} className="p-2 text-right">Total:</td>
                  <td className="p-2 text-right">{formatCurrency(data.total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </Dialog>
  );
}

// ─── NUEVA CON XML ────────────────────────────────────────────────
function NuevaXmlTab({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>(1);
  const [parsed, setParsed] = useState<ParsedInvoice | null>(null);
  const [items, setItems] = useState<EditableItem[]>([]);
  const [supplierId, setSupplierId] = useState<string>('');
  const [supplierName, setSupplierName] = useState<string>('');
  const [createNewSupplier, setCreateNewSupplier] = useState(false);
  const [newSupplier, setNewSupplier] = useState<SupplierIn>({ nit: '', name: '' });
  const [folio, setFolio] = useState('');
  const [transportCost, setTransportCost] = useState(0);
  const parseMut = useMutation({
    mutationFn: (file: File) => purchases.parseXml(file),
    onSuccess: (data) => {
      setParsed(data);
      setFolio(data.folio || '');
      if (data.supplier.matched_supplier_id) {
        setSupplierId(data.supplier.matched_supplier_id);
        setSupplierName(data.supplier.name || '');
      } else if (data.supplier.nit) {
        setCreateNewSupplier(true);
        setNewSupplier({
          nit: data.supplier.nit,
          name: data.supplier.name || '',
          email: data.supplier.email || '',
          phone: data.supplier.phone || '',
          address: data.supplier.address || '',
        });
      }
      setItems(data.items.map((it, i) => ({
        ...it,
        _id: `item-${i}`,
        factor_pack: 1,
        margen_pct: DEFAULT_MARGIN,
      })));
      setStep(2);
      toast.success(`XML procesado: ${data.items.length} items detectados`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const saveMut = useMutation({
    mutationFn: async () => {
      let finalSupplierId = supplierId;
      let finalSupplierName = supplierName;

      if (createNewSupplier) {
        if (!newSupplier.name.trim()) throw new Error('El nombre del proveedor es requerido');
        const created = await suppliersApi.create(newSupplier);
        finalSupplierId = created.id;
        finalSupplierName = created.name;
      }

      const effectiveName = finalSupplierName || newSupplier.name;
      if (!effectiveName.trim()) throw new Error('Selecciona o crea un proveedor antes de guardar');

      const matchedItems = items.filter((it) => it.suggested_product_id);
      if (matchedItems.length === 0) throw new Error('Debes asociar al menos un producto antes de guardar');

      const totalCost = matchedItems.reduce((s, it) => s + it.cantidad * it.costo_base_unitario, 0);
      const totalUnits = matchedItems.reduce((s, it) => s + it.cantidad, 0);
      const transportPerUnit = totalCost > 0 && totalUnits > 0 ? transportCost / totalUnits : 0;

      return purchases.create({
        folio: folio || undefined,
        supplier_id: finalSupplierId || undefined,
        supplier_name: effectiveName,
        items: matchedItems
          .map((it) => ({
            product_id: it.suggested_product_id!,
            sku_proveedor: it.sku_proveedor || undefined,
            sku_interno: it.suggested_product_sku || undefined,
            product_name: it.suggested_product_name || it.descripcion,
            quantity: Math.round(it.cantidad),
            factor_pack: it.factor_pack,
            unit_cost: it.costo_base_unitario + transportPerUnit,
            tax_pct: it.iva_pct,
          })),
        receive_now: true,
      });
    },
    onSuccess: () => {
      toast.success('Compra registrada correctamente');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const totals = useMemo(() => {
    const subtotal = items.reduce((s, it) => s + it.cantidad * it.costo_base_unitario, 0);
    const tax = items.reduce((s, it) => s + it.cantidad * it.costo_base_unitario * (it.iva_pct / 100), 0);
    return { subtotal, tax, total: subtotal + tax + transportCost };
  }, [items, transportCost]);

  const unmatchedCount = items.filter((it) => !it.suggested_product_id).length;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                step >= n ? 'bg-orange-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}>{n}</div>
              <span className={step === n ? 'font-bold' : 'text-gray-500'}>
                {n === 1 ? 'Cargar XML' : n === 2 ? 'Revisar y Asociar' : 'Confirmar'}
              </span>
              {n < 3 && <div className="w-12 h-0.5 bg-gray-300" />}
            </div>
          ))}
        </div>
      </Card>

      {step === 1 && (
        <Card className="p-12 text-center">
          <FileUp className="h-16 w-16 mx-auto text-orange-500 mb-4" />
          <h3 className="text-xl font-bold mb-2">Sube el XML de la factura DIAN</h3>
          <p className="text-gray-600 mb-6">Soporta formato Invoice o AttachedDocument (UBL)</p>
          <label
            htmlFor="xml-upload-input"
            className={`inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold cursor-pointer transition
              ${parseMut.isPending
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-orange-500 hover:bg-orange-600 text-white'}`}
          >
            <Upload className="h-4 w-4" />
            {parseMut.isPending ? 'Procesando XML...' : 'Seleccionar archivo XML'}
          </label>
          <input
            id="xml-upload-input"
            type="file"
            accept=".xml,text/xml,application/xml"
            className="sr-only"
            disabled={parseMut.isPending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                parseMut.mutate(file);
                e.target.value = '';
              }
            }}
          />
        </Card>
      )}

      {step === 2 && parsed && (
        <>
          <Card className="p-4">
            <h3 className="font-bold mb-3 flex items-center gap-2"><Truck className="h-4 w-4" />Proveedor</h3>
            {parsed.supplier.matched_supplier_id ? (
              <div className="bg-green-50 border border-green-200 rounded p-3 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-bold text-green-900">{supplierName}</p>
                  <p className="text-xs text-green-700">Proveedor existente reconocido por NIT {parsed.supplier.nit}</p>
                </div>
              </div>
            ) : createNewSupplier ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 space-y-2">
                <div className="flex items-center gap-2 text-yellow-900">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-bold">Proveedor nuevo — se creará al guardar</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="NIT" value={newSupplier.nit} onChange={(e) => setNewSupplier({ ...newSupplier, nit: e.target.value })} />
                  <Input placeholder="Nombre" value={newSupplier.name} onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })} />
                  <Input placeholder="Email" value={newSupplier.email || ''} onChange={(e) => setNewSupplier({ ...newSupplier, email: e.target.value })} />
                  <Input placeholder="Teléfono" value={newSupplier.phone || ''} onChange={(e) => setNewSupplier({ ...newSupplier, phone: e.target.value })} />
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-3 gap-3 mt-3">
              <div>
                <label className="text-sm">Folio factura</label>
                <Input value={folio} onChange={(e) => setFolio(e.target.value)} />
              </div>
              <div>
                <label className="text-sm">Costo de transporte</label>
                <Input type="number" value={transportCost} onChange={(e) => setTransportCost(Number(e.target.value))} />
              </div>
              <div className="text-sm">
                <p className="text-gray-500">Subtotal: {formatCurrency(totals.subtotal)}</p>
                <p className="text-gray-500">IVA: {formatCurrency(totals.tax)}</p>
                <p className="font-bold">Total: {formatCurrency(totals.total)}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold">Items ({items.length}) — Asociación inteligente</h3>
              {unmatchedCount > 0 && (
                <Badge className="bg-red-100 text-red-700">
                  <AlertTriangle className="h-3 w-3 mr-1" />{unmatchedCount} sin asociar
                </Badge>
              )}
            </div>

            <div className="overflow-auto max-h-[500px]">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left p-2">SKU Prov</th>
                    <th className="text-left p-2">Descripción XML</th>
                    <th className="text-right p-2">Cant</th>
                    <th className="text-right p-2">Costo Unit</th>
                    <th className="text-left p-2">Producto Asociado</th>
                    <th className="text-center p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <ItemRow
                      key={it._id}
                      item={it}
                      onChange={(updated) => setItems(items.map(x => x._id === it._id ? updated : x))}
                      onRemove={() => setItems(items.filter(x => x._id !== it._id))}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>Atrás</Button>
            <Button onClick={() => setStep(3)} className="bg-orange-500 hover:bg-orange-600">
              Siguiente: Confirmar
            </Button>
          </div>
        </>
      )}

      {step === 3 && (
        <Card className="p-6 space-y-4">
          <h3 className="text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="h-6 w-6 text-green-600" />Confirmación
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><strong>Proveedor:</strong> {createNewSupplier ? newSupplier.name : supplierName}</div>
            <div><strong>Folio:</strong> {folio || '—'}</div>
            <div><strong>Items asociados:</strong> {items.filter(i => i.suggested_product_id).length} / {items.length}</div>
            <div><strong>Total:</strong> {formatCurrency(totals.total)}</div>
          </div>

          {unmatchedCount > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
              <AlertTriangle className="h-4 w-4 inline text-yellow-700" /> Hay {unmatchedCount} items sin producto asociado. Solo se guardarán los asociados.
            </div>
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>Atrás</Button>
            <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="bg-green-600 hover:bg-green-700">
              <Save className="h-4 w-4 mr-2" />
              {saveMut.isPending ? 'Guardando...' : 'Confirmar y registrar compra'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function ItemRow({ item, onChange, onRemove }: { item: EditableItem; onChange: (i: EditableItem) => void; onRemove: () => void }) {
  const [picking, setPicking] = useState(false);

  const matchBadge = () => {
    if (!item.match_reason) return <Badge className="bg-red-100 text-red-700">Sin asociar</Badge>;
    const colorMap: Record<string, string> = {
      memoria: 'bg-green-100 text-green-700',
      sku_exacto: 'bg-blue-100 text-blue-700',
      nombre_exacto: 'bg-blue-100 text-blue-700',
      fuzzy: 'bg-yellow-100 text-yellow-700',
    };
    const cls = colorMap[item.match_reason] || 'bg-gray-100 text-gray-700';
    const label = item.match_reason === 'memoria' ? '🧠 Memoria'
      : item.match_reason === 'sku_exacto' ? '🎯 SKU exacto'
      : item.match_reason === 'nombre_exacto' ? '🎯 Nombre exacto'
      : item.match_reason === 'fuzzy' ? `🔍 ${Math.round((item.match_score || 0) * 100)}%`
      : item.match_reason;
    return <Badge className={cls}>{label}</Badge>;
  };

  return (
    <>
      <tr className="border-t">
        <td className="p-2 font-mono">{item.sku_proveedor || '—'}</td>
        <td className="p-2 max-w-[200px] truncate">{item.descripcion}</td>
        <td className="p-2 text-right">{item.cantidad}</td>
        <td className="p-2 text-right">{formatCurrency(item.costo_base_unitario)}</td>
        <td className="p-2">
          {item.suggested_product_id ? (
            <div>
              <p className="font-medium">{item.suggested_product_name}</p>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-xs text-gray-500">{item.suggested_product_sku}</span>
                {matchBadge()}
              </div>
            </div>
          ) : (
            matchBadge()
          )}
        </td>
        <td className="p-2 text-center">
          <Button size="sm" variant="outline" onClick={() => setPicking(true)}>
            <Search className="h-3 w-3" />
          </Button>
          <Button size="sm" variant="outline" onClick={onRemove} className="ml-1 text-red-600">
            <X className="h-3 w-3" />
          </Button>
        </td>
      </tr>
      {picking && (
        <ProductPickerDialog
          query={item.descripcion}
          onPick={(p) => {
            onChange({
              ...item,
              suggested_product_id: p.id,
              suggested_product_sku: p.sku,
              suggested_product_name: p.name,
              match_reason: 'manual',
              match_score: 1,
            });
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
    </>
  );
}

function ProductPickerDialog({ query, onPick, onClose }: { query: string; onPick: (p: { id: string; sku: string; name: string }) => void; onClose: () => void }) {
  const [search, setSearch] = useState(query);
  const { data, isLoading } = useQuery({
    queryKey: ['products-picker', search],
    queryFn: () => productsApi.list({ q: search, page_size: 30 }),
  });

  return (
    <Dialog open onClose={onClose} title="Seleccionar producto" size="lg">
      <DialogBody>
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar..." className="mb-3" />
        {isLoading ? <div className="text-center py-4">Buscando...</div> : (
          <div className="max-h-96 overflow-auto space-y-1">
            {data?.items.map((p) => (
              <button
                key={p.id}
                onClick={() => onPick(p)}
                className="w-full text-left p-2 hover:bg-orange-50 rounded border"
              >
                <p className="font-medium">{p.name}</p>
                <p className="text-xs text-gray-500">SKU: {p.sku}</p>
              </button>
            ))}
          </div>
        )}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
      </DialogFooter>
    </Dialog>
  );
}

// ─── NUEVA MANUAL ─────────────────────────────────────────────────
function NuevaManualTab({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [supplierId, setSupplierId] = useState('');
  const [supplierName, setSupplierName] = useState('');
  const [folio, setFolio] = useState('');
  const [items, setItems] = useState<EditableItem[]>([]);
  const [picking, setPicking] = useState(false);

  const supList = useQuery({ queryKey: ['suppliers-all'], queryFn: () => suppliersApi.list({ is_active: true, page_size: 200 }) });

  const saveMut = useMutation({
    mutationFn: () => purchases.create({
      folio: folio || undefined,
      supplier_id: supplierId || undefined,
      supplier_name: supplierName,
      items: items.map((it) => ({
        product_id: it.suggested_product_id!,
        product_name: it.suggested_product_name!,
        quantity: it.cantidad,
        factor_pack: it.factor_pack,
        unit_cost: it.costo_base_unitario,
        tax_pct: it.iva_pct,
      })),
      receive_now: true,
    }),
    onSuccess: () => {
      toast.success('Compra registrada');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const total = items.reduce((s, it) => s + it.cantidad * it.costo_base_unitario * (1 + it.iva_pct / 100), 0);

  return (
    <div className="space-y-4">
      <Card className="p-4 grid grid-cols-3 gap-3">
        <div>
          <label className="text-sm">Proveedor</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={supplierId}
            onChange={(e) => {
              const s = supList.data?.items.find(x => x.id === e.target.value);
              setSupplierId(e.target.value);
              setSupplierName(s?.name || '');
            }}
          >
            <option value="">— Selecciona —</option>
            {supList.data?.items.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm">Folio</label>
          <Input value={folio} onChange={(e) => setFolio(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button onClick={() => setPicking(true)} className="bg-orange-500 hover:bg-orange-600 w-full">
            <Plus className="h-4 w-4 mr-1" />Agregar producto
          </Button>
        </div>
      </Card>

      <Card>
        {!items.length ? (
          <div className="p-12 text-center text-gray-500">Agrega productos a la compra</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2">Producto</th>
                <th className="text-right p-2">Cant</th>
                <th className="text-right p-2">Costo</th>
                <th className="text-right p-2">IVA%</th>
                <th className="text-right p-2">Total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={it._id} className="border-t">
                  <td className="p-2">{it.suggested_product_name}</td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.cantidad} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, cantidad: v } : x));
                    }} className="w-20 text-right" />
                  </td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.costo_base_unitario} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, costo_base_unitario: v } : x));
                    }} className="w-28 text-right" />
                  </td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.iva_pct} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, iva_pct: v } : x));
                    }} className="w-16 text-right" />
                  </td>
                  <td className="p-2 text-right font-bold">
                    {formatCurrency(it.cantidad * it.costo_base_unitario * (1 + it.iva_pct / 100))}
                  </td>
                  <td className="p-2 text-center">
                    <Button size="sm" variant="outline" onClick={() => setItems(items.filter(x => x._id !== it._id))} className="text-red-600">
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t font-bold">
                <td colSpan={4} className="p-2 text-right">Total:</td>
                <td className="p-2 text-right">{formatCurrency(total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        )}
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={() => saveMut.mutate()}
          disabled={!supplierName || !items.length || saveMut.isPending}
          className="bg-green-600 hover:bg-green-700"
        >
          <Save className="h-4 w-4 mr-2" />Registrar compra
        </Button>
      </div>

      {picking && (
        <ProductPickerDialog
          query=""
          onPick={(p) => {
            setItems([...items, {
              _id: `m-${Date.now()}`,
              sku_proveedor: null,
              descripcion: p.name,
              cantidad: 1,
              costo_base_unitario: 0,
              iva_pct: 19,
              descuento: 0,
              total_linea: 0,
              suggested_product_id: p.id,
              suggested_product_sku: p.sku,
              suggested_product_name: p.name,
              match_reason: 'manual',
              match_score: 1,
              factor_pack: 1,
              margen_pct: DEFAULT_MARGIN,
            }]);
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
    </div>
  );
}
