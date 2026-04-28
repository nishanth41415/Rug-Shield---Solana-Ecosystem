import { Route, Routes } from 'react-router-dom'
import LiveTokenFeed from './components/LiveTokenFeed'
import TokenDetailPage from './pages/TokenDetailPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LiveTokenFeed />} />
      <Route path="/token/:mint" element={<TokenDetailPage />} />
    </Routes>
  )
}

export default App
