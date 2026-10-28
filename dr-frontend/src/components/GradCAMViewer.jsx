import { useState } from "react";

export default function GradCAMViewer({ originalPreview, gradcam, conditionLabel }) {
  const [viewMode, setViewMode] = useState("overlay"); // "overlay" | "side-by-side" | "original"
  const [opacity, setOpacity] = useState(50); // 0% to 100%

  if (!gradcam && !originalPreview) return null;

  const hasGradcam = Boolean(gradcam && gradcam.heatmap_overlay);

  return (
    <div className="gradcam-card">
      <div className="gradcam-header">
        <div>
          <h4>Explainable AI (Grad-CAM Heatmap)</h4>
          <p className="gradcam-subtitle">
            Visual activation map highlighting lesion regions driving the {conditionLabel || "prediction"}
          </p>
        </div>

        {/* View Mode Switcher */}
        {hasGradcam && (
          <div className="gradcam-view-tabs" role="tablist">
            <button
              type="button"
              className={`view-tab-btn ${viewMode === "overlay" ? "active" : ""}`}
              onClick={() => setViewMode("overlay")}
            >
              Overlay
            </button>
            <button
              type="button"
              className={`view-tab-btn ${viewMode === "side-by-side" ? "active" : ""}`}
              onClick={() => setViewMode("side-by-side")}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              className={`view-tab-btn ${viewMode === "original" ? "active" : ""}`}
              onClick={() => setViewMode("original")}
            >
              Original
            </button>
          </div>
        )}
      </div>

      {/* Main Visual Display */}
      <div className="gradcam-viewport">
        {viewMode === "side-by-side" && hasGradcam ? (
          <div className="side-by-side-grid">
            <div className="side-panel">
              <span className="side-label">Original Fundus</span>
              <div className="img-frame">
                <img src={originalPreview} alt="Original Retinal Scan" />
              </div>
            </div>
            <div className="side-panel">
              <span className="side-label">AI Attention Map</span>
              <div className="img-frame">
                <img src={gradcam.heatmap_overlay} alt="Grad-CAM Heatmap Overlay" />
              </div>
            </div>
          </div>
        ) : viewMode === "original" || !hasGradcam ? (
          <div className="single-view-frame">
            <img src={originalPreview} alt="Original Retinal Scan" />
            <span className="view-badge">Original Fundus Scan</span>
          </div>
        ) : (
          /* Overlay Mode with interactive Opacity */
          <div className="interactive-overlay-wrapper">
            <div className="stacked-images-container">
              {/* Layer 1: Base original image */}
              <img
                src={originalPreview}
                alt="Base Fundus"
                className="base-fundus-layer"
              />

              {/* Layer 2: Raw Heatmap or Overlay with adjustable opacity */}
              {gradcam.heatmap_raw ? (
                <img
                  src={gradcam.heatmap_raw}
                  alt="Heatmap Layer"
                  className="heatmap-mask-layer"
                  style={{ opacity: opacity / 100 }}
                />
              ) : (
                <img
                  src={gradcam.heatmap_overlay}
                  alt="Heatmap Overlay"
                  className="heatmap-mask-layer"
                  style={{ opacity: opacity / 100 }}
                />
              )}
            </div>

            <span className="view-badge">Grad-CAM Overlay ({opacity}%)</span>
          </div>
        )}
      </div>

      {/* Heatmap Controls & Legend */}
      {hasGradcam && (
        <div className="gradcam-controls-panel">
          {viewMode === "overlay" && (
            <div className="opacity-slider-control">
              <label htmlFor="heatmap-opacity-range">
                <span>Heatmap Opacity:</span>
                <strong>{opacity}%</strong>
              </label>
              <input
                id="heatmap-opacity-range"
                type="range"
                min="0"
                max="100"
                value={opacity}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="opacity-range-input"
              />
            </div>
          )}

          {/* Attention Intensity Legend */}
          <div className="heatmap-legend">
            <span className="legend-title">Attention:</span>
            <span className="legend-label">Normal</span>
            <div className="legend-spectrum-bar" />
            <span className="legend-label high">High (Lesions)</span>
          </div>
        </div>
      )}

      <div className="gradcam-clinical-note">
        <strong>Clinical interpretation:</strong> Red and warm spectrum areas denote retinal feature activations with greatest weight in classification (e.g., microaneurysms, hemorrhages, or exudates). Cool/blue areas represent standard retinal background.
      </div>
    </div>
  );
}
