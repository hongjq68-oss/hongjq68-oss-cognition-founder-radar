import { useEffect, useState } from "react";
import { api, type Any } from "../api";
import { Badge, PageHeader } from "../components/ui";
import { useApp } from "../ctx";

const tone: Record<string, string> = { Live: "green", "Live (manual URL)": "green", "Requires approval": "amber", "Requires API key": "amber", "Not supported": "red" };

export default function Sources() {
  const { can, toast } = useApp();
  const [rows, setRows] = useState<Any[]>([]);
  const load = () => api.sources().then(setRows);
  useEffect(() => { load(); }, []);
  return (
    <div>
      <PageHeader title="Source integrations" subtitle="Approved public or authorised sources only. Connectors respect robots.txt, platform terms and authentication — no scraping of private data." />
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Source", "Type", "Access / authorisation", "Status", "People", "Last run", "Enabled"].map((h) => <th key={h} className="p-3">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((s) => (
              <tr key={s.key} className="align-top">
                <td className="p-3"><div className="font-medium text-slate-900">{s.name}</div><div className="text-xs text-slate-500 max-w-md">{s.description}</div></td>
                <td className="p-3 text-xs">{s.kind}</td>
                <td className="p-3 text-xs text-slate-600">{s.access}</td>
                <td className="p-3"><Badge tone={tone[s.status]}>{s.status}</Badge></td>
                <td className="p-3">{s.people}</td>
                <td className="p-3 text-xs text-slate-500">{s.last_run_at?.slice(0, 16).replace("T", " ") ?? "—"}{s.last_result && <div>{typeof s.last_result === "string" ? s.last_result : JSON.stringify(s.last_result)}</div>}</td>
                <td className="p-3">
                  <input type="checkbox" checked={s.enabled} disabled={!can("admin") || s.status === "Not supported"}
                    onChange={async (e) => { try { await api.toggleSource(s.key, e.target.checked); load(); } catch (x) { toast((x as Error).message); } }} />
                  {s.approved_by && <div className="text-[11px] text-slate-400">{s.approved_by}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-3">Only admins can approve/enable a source. Sources needing a partner agreement or API key stay disabled until approved.</p>
    </div>
  );
}
