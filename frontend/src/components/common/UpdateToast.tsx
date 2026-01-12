import { toast, type Toast } from "react-hot-toast";

interface UpdateToastProps {
  t: Toast;
  text: string;
  url: string;
}

export const UpdateToast = ({ t, text, url }: UpdateToastProps) => (
  <div className="flex flex-col gap-2">
    <span className="font-bold">New Version Available! 🚀</span>
    <span className="text-sm">{text}</span>
    <div className="flex gap-2 mt-1">
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="px-3 py-1 bg-primary text-black rounded-lg text-xs font-bold hover:opacity-90"
        onClick={() => toast.dismiss(t.id)}
      >
        View
      </a>
      <button
        onClick={() => toast.dismiss(t.id)}
        className="px-3 py-1 bg-white/10 rounded-lg text-xs hover:bg-white/20"
      >
        Dismiss
      </button>
    </div>
  </div>
);
