export default function ProbabilityChart({ probabilities, predictedClass }) {
  if (!probabilities || probabilities.length === 0) return null;

  return (
    <div className="prob-chart-container">
      <div className="prob-chart-header">
        <div>
          <h4>All 5-Class Probability Distribution</h4>
          <span className="prob-subtitle">
            Full softmax confidence scores across all diabetic retinopathy clinical stages
          </span>
        </div>
      </div>

      <div className="prob-bars-list">
        {probabilities.map((item) => {
          const isHighest = item.is_predicted || item.class_name === predictedClass;
          const pct = Math.max(0, Math.min(100, item.probability_percent || 0));

          return (
            <div
              key={item.class_name}
              className={`prob-bar-row ${isHighest ? "prob-row-selected" : ""}`}
            >
              <div className="prob-meta-left">
                <span
                  className="prob-level-badge"
                  style={{ backgroundColor: item.color || "#0f6e73" }}
                  title={`Severity Level ${item.level}`}
                >
                  L{item.level}
                </span>
                <span className="prob-class-name">
                  {item.label || item.class_name}
                  {isHighest && <span className="prob-winner-tag">Primary Match</span>}
                </span>
              </div>

              <div className="prob-meter-wrapper">
                <div className="prob-track">
                  <div
                    className="prob-fill"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: item.color || "#0f6e73",
                    }}
                  />
                </div>
                <span className="prob-pct-value">
                  {pct.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="prob-chart-footer">
        <span className="prob-note">
          ℹ High confidence in Level 2+ indicates priority referral for clinical evaluation.
        </span>
      </div>
    </div>
  );
}
