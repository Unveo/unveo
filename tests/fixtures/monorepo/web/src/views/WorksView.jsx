import { t } from "../i18n";
export function WorksView({ works }) {
  return <table>{works.map(w => <tr key={w.id}><td>{w.name}</td><td>{w.priority_score}</td></tr>)}</table>;
}
