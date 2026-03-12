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
        {topSlot ? <header className="app-shell__top">{topSlot}</header> : null}
        <main className="app-shell__main">{children}</main>
        {bottomSlot ? <footer className="app-shell__bottom">{bottomSlot}</footer> : null}
      </div>
    </div>
  );
}
