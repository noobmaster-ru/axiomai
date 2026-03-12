import type { ReactNode } from "react";
import "./AppShell.css";

type AppShellProps = {
  mode?: "app" | "flow";
  topSlot?: ReactNode;
  bottomSlot?: ReactNode;
  children: ReactNode;
};

export function AppShell({ mode = "app", topSlot, bottomSlot, children }: AppShellProps) {
  return (
    <div className={`app-shell app-shell--${mode}`}>
      <div className="app-shell__frame">
        {topSlot ? <header className="app-shell__top">{topSlot}</header> : null}
        <main className="app-shell__main">{children}</main>
        {bottomSlot ? <footer className="app-shell__bottom">{bottomSlot}</footer> : null}
      </div>
    </div>
  );
}
