import { Component } from 'react';

/**
 * Catches render errors in the child tree and shows a recoverable fallback.
 * Without this, a single bad trace response or malformed file could blank
 * the page with no way back except a full reload.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
    this.setState({ info });
  }

  reset = () => {
    this.setState({ error: null, info: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
          <div className="max-w-lg w-full bg-white border border-rose-200 rounded-lg p-6 shadow-sm">
            <div className="text-3xl mb-2">⚠️</div>
            <h2 className="text-lg font-semibold text-slate-800 mb-1">
              Something rendered badly
            </h2>
            <p className="text-sm text-slate-600 mb-3">
              The UI caught an error and bailed out of that view. You can try again without
              losing your session.
            </p>
            <pre className="text-[11px] font-mono bg-slate-100 text-slate-700 p-2 rounded mb-3 max-h-48 overflow-auto whitespace-pre-wrap">
              {String(this.state.error?.message || this.state.error)}
            </pre>
            <div className="flex gap-2">
              <button
                onClick={this.reset}
                className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded"
              >
                Try again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded"
              >
                Reload app
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
