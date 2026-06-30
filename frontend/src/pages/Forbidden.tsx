import { Link } from 'react-router-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

export default function Forbidden() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-4 text-9xl font-bold text-foreground">403</h1>
        <h2 className="mb-8 text-4xl font-semibold text-foreground">Access Denied</h2>

        <Alert variant="destructive" className="mb-8 text-left">
          <AlertTitle>Forbidden</AlertTitle>
          <AlertDescription>
            You don't have permission to access this page. Please contact your administrator if you
            believe this is a mistake.
          </AlertDescription>
        </Alert>

        <Button asChild>
          <Link to="/">Go Home</Link>
        </Button>
      </div>
    </div>
  )
}
