import { useState } from 'react';

interface ToggleSwitchProps {
  label: string;
  defaultChecked?: boolean;
  onChange?: (checked: boolean) => void;
}

export function ToggleSwitch({ label, defaultChecked = false, onChange }: ToggleSwitchProps) {
  const [checked, setChecked] = useState(defaultChecked);

  const handleToggle = () => {
    const newChecked = !checked;
    setChecked(newChecked);
    onChange?.(newChecked);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleToggle}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          checked ? 'bg-emerald-600' : 'bg-gray-600'
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-0'
          }`}
        />
      </button>
      <span className="text-gray-300">{label}</span>
    </div>
  );
}
