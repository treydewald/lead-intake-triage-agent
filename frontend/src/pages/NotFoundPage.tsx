import { Link } from 'react-router-dom'
import { CompassIcon } from 'lucide-react'
import { EmptyState } from '../components/ui/States'

export function NotFoundPage() {
  return (
    <EmptyState
      icon={CompassIcon}
      title="This page doesn't exist"
      description="Check the URL, or head back to the home page."
      action={
        <Link
          to="/"
          className="inline-flex w-fit items-center rounded-lg bg-teal-700 px-4 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-800"
        >
          Back to home
        </Link>
      }
    />
  )
}
