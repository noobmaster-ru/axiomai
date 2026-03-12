import type { ReactNode } from "react";
import { FlowProgress } from "./FlowProgress";
import type { FlowStepKey } from "./flowSteps";
import "./FlowLayout.css";

type FlowLayoutProps = {
  activeStep: FlowStepKey;
  actionSlot: ReactNode;
  children: ReactNode;
  description?: string;
  onBack: () => void;
  title: string;
};

export function FlowLayout({
  activeStep,
  actionSlot,
  children,
  description,
  onBack,
  title,
}: FlowLayoutProps) {
  return (
    <div className="flow-layout">
      <div className="flow-layout__header">
        <button className="flow-layout__back" type="button" onClick={onBack}>
          Назад
        </button>

        <div className="flow-layout__heading">
          <p className="flow-layout__eyebrow">Оформление заявки</p>
          <h1 className="flow-layout__title">{title}</h1>
          {description ? <p className="flow-layout__description">{description}</p> : null}
        </div>
      </div>

      <FlowProgress activeStep={activeStep} />

      <div className="flow-layout__body">{children}</div>

      <div className="flow-layout__footer">{actionSlot}</div>
    </div>
  );
}
