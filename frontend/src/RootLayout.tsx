import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import { ThemeModeProvider } from './theme/ThemeModeProvider.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <App />
      </ThemeModeProvider>
    </QueryClientProvider>
  )
}
