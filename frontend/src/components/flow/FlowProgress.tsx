import { flowSteps, type FlowStepKey } from "./flowSteps";
import "./FlowProgress.css";

type FlowProgressProps = {
  activeStep: FlowStepKey;
};

export function FlowProgress({ activeStep }: FlowProgressProps) {
  const activeIndex = flowSteps.findIndex((step) => step.key === activeStep);

  return (
    <div className="flow-progress" aria-label="Прогресс заявки">
      <div className="flow-progress__meta">
        <span className="flow-progress__eyebrow">Шаг {activeIndex + 1} из {flowSteps.length}</span>
      </div>

      <div className="flow-progress__track" role="list">
        {flowSteps.map((step, index) => {
          const isActive = step.key === activeStep;
          const isCompleted = index < activeIndex;

          return (
            <div
              key={step.key}
              className={`flow-progress__step${isActive ? " flow-progress__step--active" : ""}${isCompleted ? " flow-progress__step--completed" : ""}`}
              role="listitem"
              aria-current={isActive ? "step" : undefined}
            >
              <span className="flow-progress__bullet">{index + 1}</span>
              <span className="flow-progress__label">{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
