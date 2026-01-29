import { Copy } from 'lucide-react';

interface CopyButtonProps {
  text: string;
}

export function CopyButton({ text }: CopyButtonProps) {
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 bg-[#2a3142] hover:bg-[#343d52] border border-gray-600 rounded text-gray-400 hover:text-gray-300 transition-colors"
    >
      <Copy className="w-4 h-4" />
    </button>
  );
}
