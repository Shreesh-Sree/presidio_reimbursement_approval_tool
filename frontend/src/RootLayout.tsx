import { ClerkProvider } from '@clerk/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import App from './App.tsx'
import { clerkPublishableKey, isClerkConfigured } from './auth/clerk.tsx'
import { ThemeModeProvider } from './theme/ThemeModeProvider.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export function RootLayout() {
  const navigate = useNavigate()
  const content = (
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <App />
      </ThemeModeProvider>
    </QueryClientProvider>
  )

  // Keep the explicit configuration screen usable before a public Clerk key
  // exists. When configured, pass that public key at the application entry
  // point so Clerk can initialize its browser session context.
  if (!isClerkConfigured) return content

  return (
    <ClerkProvider
      publishableKey={clerkPublishableKey}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
    >
      {content}
    </ClerkProvider>
  )
}
