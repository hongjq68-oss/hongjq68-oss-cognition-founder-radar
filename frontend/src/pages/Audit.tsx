import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Any } from "../api";
import { PageHeader } from "../components/ui";

export default function Audit() {
  const [rows, setRows] = useState<Any[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => { api.audit().then(setRows); }, []);
  const f = rows.filter((r) => !q || JSON.stringify(r).toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader title="Audit log" subtitle="Every write, verification, approval, import and export." />
      <input className="input max-w-sm mb-4" placeholder="Filter by user, action, entity…" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Time (UTC)", "User", "Action", "Entity", "Detail"].map((h) => <th key={h} className="p-3">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">
            {f.map((r) => (
              <tr key={r.id}>
                <td className="p-3 text-xs text-slate-500 whitespace-nowrap">{r.ts.slice(0, 19).replace("T", " ")}</td>
                <td className="p-3">{r.user}</td>
                <td className="p-3 font-mono text-xs text-brand-700">{r.action}</td>
                <td className="p-3 text-xs">{r.entity === "person" && r.entity_id ? <Link className="hover:underline" to={`/people/${r.entity_id}`}>person #{r.entity_id}</Link> : `${r.entity}${r.entity_id ? " #" + r.entity_id : ""}`}</td>
                <td className="p-3 text-xs text-slate-500 break-all max-w-lg">{JSON.stringify(r.detail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
