import { ProjectTable } from "../../../components/ProjectTable";
export default async function StatePage({ params }) {
  const res = await fetch(`/api/projects?state=${params.state}`);
  return (<section><input placeholder="Search projects" name="q" />
    <form action="/search"><select name="status"></select><button type="submit">Search</button></form>
    <ProjectTable rows={await res.json()} /></section>);
}
