import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AuthPage from '@/pages/AuthPage';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<AuthPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;

