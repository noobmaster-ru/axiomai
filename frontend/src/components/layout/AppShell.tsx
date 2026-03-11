import type { ReactNode } from "react";
import "./AppShell.css";

type AppShellProps = {
  topSlot?: ReactNode;
  bottomSlot?: ReactNode;
  children: ReactNode;
};

export function AppShell({ topSlot, bottomSlot, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="app-shell__frame">
        <header className="app-shell__top">{topSlot}</header>
        <main className="app-shell__main">{children}</main>
        <footer className="app-shell__bottom">{bottomSlot}</footer>
      </div>
    </div>
  );
}
