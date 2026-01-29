import { ReactNode } from 'react';

interface ConfigFieldProps {
  label: string;
  children: ReactNode;
}

export function ConfigField({ label, children }: ConfigFieldProps) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-gray-300">{label}</label>
      <div className="flex items-center gap-2">
        {children}
      </div>
    </div>
  );
}
