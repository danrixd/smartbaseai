import AppRouter from './router';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

export default function App() {
  return (
    <ErrorBoundary>
      <AppRouter />
    </ErrorBoundary>
  );
}
