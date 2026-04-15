/**
 * Blocking placeholder shown when the current page needs an active vault
 * but none has been picked yet. Super-admins start in this state by design —
 * they can see every vault but must choose one first, so that retrieval,
 * chat, and editing are always explicitly scoped.
 */
export default function VaultGate({ role, title = 'Pick a vault to continue' }) {
  return (
    <div className="flex-1 flex items-center justify-center bg-slate-50 p-6">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-lg p-6 shadow-sm text-center">
        <div className="text-5xl mb-3">🗂️</div>
        <h2 className="text-lg font-semibold text-slate-800 mb-2">{title}</h2>
        <p className="text-sm text-slate-600">
          {role === 'super_admin'
            ? 'You have access to every vault. Use the "Active vault" dropdown at the top of the page to pick one before chatting, running retrieval traces, or editing files.'
            : 'No vault is associated with your account. Contact an administrator to be assigned to a tenant.'}
        </p>
      </div>
    </div>
  );
}
