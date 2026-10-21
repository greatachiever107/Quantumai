import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

const TONE: Record<string, string> = {
  brand: "bg-brand/15 text-blue-600 dark:text-blue-400", info: "bg-info/15 text-info",
  warn: "bg-warn/15 text-warn", ai: "bg-ai/15 text-ai", up: "bg-up/15 text-up",
};

export default function Title({ icon: Icon, tone = "brand", children, mb = "mb-3" }: {
  icon: LucideIcon; tone?: string; children: ReactNode; mb?: string;
}) {
  return (
    <div className={`${mb} flex items-center gap-2.5`}>
      <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg ${TONE[tone] ?? TONE.brand}`}><Icon className="h-4 w-4" /></div>
      <div className="text-base font-semibold">{children}</div>
    </div>
  );
}
