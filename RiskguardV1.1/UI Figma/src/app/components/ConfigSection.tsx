import { ReactNode, useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

interface ConfigSectionProps {
  title: string;
  icon: ReactNode;
  iconColor: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export function ConfigSection({ title, icon, iconColor, children, defaultOpen = true }: ConfigSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-[#1e2433] rounded-lg border border-gray-700 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#252b3c] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-5 h-5 ${iconColor}`}>
            {icon}
          </div>
          <span className="text-white">{title}</span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>
      
      {isOpen && (
        <div className="px-6 pb-6 space-y-4">
          {children}
        </div>
      )}
    </div>
  );
}
