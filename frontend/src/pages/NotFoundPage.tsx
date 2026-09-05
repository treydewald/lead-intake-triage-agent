import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-slate-600">This page doesn't exist.</p>
      <Link to="/" className="w-fit text-teal-700 hover:underline">
        Back to home
      </Link>
    </div>
  )
}
