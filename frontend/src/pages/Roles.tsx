import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { Badge, Card, PageHeader } from "../components/ui";
import { useApp } from "../ctx";

export default function Roles() {
  const { meta, can, toast } = useApp();
  const [roles, setRoles] = useState<Any[]>([]);
  const [f, setF] = useState<Any>({ name: "", description: "", angle: "", capabilities: {} });
  const load = () => api.roles().then(setRoles);
  useEffect(() => { load(); }, []);
  return (
    <div>
      <PageHeader title="Cognition roles" subtitle="Role profiles define the transferable capabilities that matching looks for (weight 1–3)." />
      <div className="grid md:grid-cols-2 gap-5">
        {roles.map((r) => (
          <Card key={r.id} title={<span className="flex items-center gap-2">{r.name}{r.custom && <Badge tone="cyan">Custom</Badge>}</span>} action={<Link className="text-xs text-brand-700" to={`/discover?role_id=${r.id}&min_fit=40`}>Find candidates</Link>}>
            <p className="text-sm text-slate-600">{r.description}</p>
            <div className="flex flex-wrap gap-1 mt-3">{Object.entries(r.capabilities).map(([k, w]) => <Badge key={k} tone={w === 3 ? "blue" : "slate"}>{meta.capabilities[k]} ×{w as number}</Badge>)}</div>
            {r.angle && <p className="text-xs text-slate-400 mt-3">Outreach angle: {r.angle}</p>}
          </Card>
        ))}
        {can("verify") && (
          <Card title="Add custom role" icon={<Plus className="h-4 w-4" />}>
            <div className="space-y-2 text-sm">
              <input className="input" placeholder="Role name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
              <textarea className="input" rows={2} placeholder="Description" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
              <input className="input" placeholder="Outreach angle" value={f.angle} onChange={(e) => setF({ ...f, angle: e.target.value })} />
              <div className="grid grid-cols-2 gap-2">{Object.entries(meta.capabilities).map(([k, l]) => (
                <label key={k} className="flex items-center justify-between gap-2 text-xs"><span>{l as string}</span>
                  <select className="input !w-16 !py-1" value={f.capabilities[k] ?? 0} onChange={(e) => { const c = { ...f.capabilities }; if (+e.target.value) c[k] = +e.target.value; else delete c[k]; setF({ ...f, capabilities: c }); }}>
                    {[0, 1, 2, 3].map((x) => <option key={x}>{x}</option>)}</select></label>))}</div>
              <button className="btn-primary" disabled={!f.name || !f.description || !Object.keys(f.capabilities).length} onClick={async () => {
                try { await api.addRole(f); toast("Role added", "ok"); setF({ name: "", description: "", angle: "", capabilities: {} }); load(); } catch (e) { toast((e as Error).message); }
              }}>Add role</button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
