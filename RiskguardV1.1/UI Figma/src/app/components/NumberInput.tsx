interface NumberInputProps {
  value: string | number;
  onChange?: (value: string) => void;
  suffix?: string;
  width?: string;
}

export function NumberInput({ value, onChange, suffix, width = 'w-20' }: NumberInputProps) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className={`${width} bg-[#2a3142] text-white px-3 py-1.5 rounded border border-gray-600 focus:border-emerald-500 focus:outline-none text-center`}
      />
      {suffix && <span className="text-gray-400">{suffix}</span>}
    </div>
  );
}
