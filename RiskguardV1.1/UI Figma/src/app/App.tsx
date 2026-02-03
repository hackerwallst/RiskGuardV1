import { RiskGuardHeader } from '@/app/components/RiskGuardHeader';
import { ConfigSection } from '@/app/components/ConfigSection';
import { ConfigField } from '@/app/components/ConfigField';
import { ToggleSwitch } from '@/app/components/ToggleSwitch';
import { NumberInput } from '@/app/components/NumberInput';
import { CopyButton } from '@/app/components/CopyButton';
import { Send, ShieldAlert, TrendingDown, Newspaper } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-[#141824]">
      <RiskGuardHeader />
      
      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Telegram Section */}
        <ConfigSection
          title="Telegram"
          icon={<Send className="w-full h-full" />}
          iconColor="text-blue-400"
        >
          <ConfigField label="Bot Token:">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value="8506125126:AAEBGNsRpqk40503Vb5wfZc6_JA38cAojZ0"
                readOnly
                className="w-[400px] bg-[#2a3142] text-gray-300 px-3 py-1.5 rounded border border-gray-600 focus:outline-none"
              />
              <CopyButton text="8506125126:AAEBGNsRpqk40503Vb5wfZc6_JA38cAojZ0" />
            </div>
          </ConfigField>

          <ConfigField label="Chat ID:">
            <input
              type="text"
              value="1199023243"
              readOnly
              className="w-40 bg-[#2a3142] text-gray-300 px-3 py-1.5 rounded border border-gray-600 focus:outline-none"
            />
          </ConfigField>

          <ConfigField label="Comandos do Telegram:">
            <ToggleSwitch label="Ativado" defaultChecked={true} />
          </ConfigField>

          <ConfigField label="Intervalo de Comandos (seg):">
            <div className="flex items-center gap-2">
              <NumberInput value="2" suffix="seg." width="w-16" />
            </div>
          </ConfigField>
        </ConfigSection>

        {/* Regras de Risco Section */}
        <ConfigSection
          title="Regras de Risco"
          icon={<ShieldAlert className="w-full h-full" />}
          iconColor="text-amber-500"
        >
          <ConfigField label="Risco Máx. por Trade:">
            <NumberInput value="1.0" suffix="%" width="w-20" />
          </ConfigField>

          <ConfigField label="Modo Interativo:">
            <div className="flex items-center gap-3">
              <ToggleSwitch label="Ativado" defaultChecked={true} />
              <span className="text-gray-400 text-sm">Timeout (Min):</span>
              <NumberInput value="15" width="w-16" />
            </div>
          </ConfigField>

          <ConfigField label="Risco Máx. Agregado:">
            <NumberInput value="5.0" suffix="%" width="w-20" />
          </ConfigField>

          <ConfigField label="Limite de Tentativas:">
            <NumberInput value="3" width="w-16" />
          </ConfigField>
        </ConfigSection>

        {/* Drawdown Section */}
        <ConfigSection
          title="Drawdown"
          icon={<TrendingDown className="w-full h-full" />}
          iconColor="text-red-400"
        >
          <ConfigField label="Limite de DD:">
            <NumberInput value="20" suffix="%" width="w-20" />
          </ConfigField>

          <ConfigField label="Cooldown (Dias):">
            <NumberInput value="30" suffix="=" width="w-20" />
          </ConfigField>
        </ConfigSection>

        {/* Janela de Notícias Section */}
        <ConfigSection
          title="Janela de Notícias"
          icon={<Newspaper className="w-full h-full" />}
          iconColor="text-blue-500"
        >
          <ConfigField label="Duração da Janela (Min):">
            <NumberInput value="60" suffix="=" width="w-20" />
          </ConfigField>

          <ConfigField label="Filtro Recentes (Seg):">
            <NumberInput value="180" suffix="=" width="w-20" />
          </ConfigField>

          <ConfigField label="Janela de Notícias:">
            <ToggleSwitch label="Desativado" defaultChecked={false} />
          </ConfigField>
        </ConfigSection>

        
        {/* Footer Status */}
        <div className="text-center py-8">
          <div className="inline-flex items-center gap-4">
            <div className="h-px flex-1 bg-gray-700 w-32"></div>
            <span className="text-gray-400 text-sm">Verificando a cada 0.7 segundos</span>
            <div className="h-px flex-1 bg-gray-700 w-32"></div>
          </div>
        </div>
      </main>
    </div>
  );
}
