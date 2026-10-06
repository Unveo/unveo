import Link from "next/link";
export default function Home() {
  return (<main><h1>Civic Watch</h1>
    <Link href="/dashboard/maharashtra">Maharashtra</Link>
    <button aria-label="View projects">View projects</button></main>);
}
