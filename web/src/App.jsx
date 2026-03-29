import { RouterProvider } from 'react-router-dom'

import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useAppMeta } from '@/hooks/useAppMeta'

import router from './router'

const getToastSwipeDirections = (position = 'top-right') => {
  switch (position) {
    case 'top-left':
      return ['top', 'left']
    case 'top-center':
      return ['top', 'left', 'right']
    case 'top-right':
      return ['top', 'right']
    case 'bottom-left':
      return ['bottom', 'left']
    case 'bottom-center':
      return ['bottom', 'left', 'right']
    case 'bottom-right':
    default:
      return ['bottom', 'right']
  }
}

function App() {
  const appMeta = useAppMeta()
  const notificationPosition = appMeta.notification_position || 'top-right'

  return (
    <ThemeProvider defaultTheme="system" storageKey="react-go-admin-theme">
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster
          richColors
          position={notificationPosition}
          duration={Number(appMeta.notification_duration) || 4000}
          visibleToasts={Number(appMeta.notification_visible_toasts) || 3}
          swipeDirections={getToastSwipeDirections(notificationPosition)}
        />
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
