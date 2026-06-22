import { useState } from 'react';
import ErrorBanner from './components/ErrorBanner.jsx';
import SearchConsole from './components/SearchConsole.jsx';

export default function App() {
  const [error, setError] = useState('');

  return (
    <main className="app-shell">
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      <SearchConsole onError={setError} />
    </main>
  );
}
