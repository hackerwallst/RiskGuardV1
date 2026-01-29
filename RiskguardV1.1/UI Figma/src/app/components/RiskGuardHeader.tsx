import { Shield, User } from 'lucide-react';

export function RiskGuardHeader() {
  return (
    <header className="bg-[#1a1f2e] border-b border-gray-700 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-[#2a3142] rounded-lg flex items-center justify-center border border-emerald-500/30">
            <Shield className="w-6 h-6 text-emerald-500" />
          </div>
          <h1 className="text-xl text-white">RiskGuard</h1>
          <span className="text-gray-400">Configurações</span>
        </div>
        
        <div className="flex items-center gap-4">
          <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-md transition-colors">
            Salvar Configurações
          </button>
          <div className="flex items-center gap-2 text-gray-300">
            <User className="w-5 h-5" />
            <span>Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
