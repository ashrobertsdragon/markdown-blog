import { Outlet } from 'react-router-dom'
import Header from './Header'

/**
 * Shell layout for all non-admin pages.
 * Renders the persistent Header above the active route via Outlet.
 */
export default function Layout() {
  return (
    <>
      <Header />
      <main>
        <Outlet />
      </main>
    </>
  )
}
