export function ProjectTable({ rows }) {
  return (<table><thead><tr><th>Project</th><th>Risk</th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id}><td>{r.name}</td><td>{r.riskScore}</td></tr>)}</tbody></table>);
}
