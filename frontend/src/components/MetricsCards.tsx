import React from "react";
import type { MetricsData } from "../services/api";

interface MetricsCardsProps {
  metrics: MetricsData;
}

export default function MetricsCards({ metrics }: MetricsCardsProps) {
  const completionRate = metrics.completion_rate ?? (metrics.total > 0 ? Math.round((metrics.completed / metrics.total) * 100) : 0);

  return (
    <div className="metrics-container">
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Total Incidencias</span>
          <span className="metric-value">{metrics.total}</span>
        </div>
        <div className="metric-card success">
          <span className="metric-label">Completados</span>
          <span className="metric-value">{metrics.completed}</span>
        </div>
        <div className="metric-card info">
          <span className="metric-label">En Progreso</span>
          <span className="metric-value">{metrics.in_progress ?? 0}</span>
        </div>
        <div className="metric-card danger">
          <span className="metric-label">Bloqueados</span>
          <span className="metric-value">{metrics.blocked}</span>
        </div>
        <div className="metric-card highlight">
          <span className="metric-label">% Completitud</span>
          <span className="metric-value">{completionRate}%</span>
        </div>
      </div>

      <div className="progress-bar-wrapper">
        <div
          className="progress-bar-fill"
          style={{ width: `${Math.min(Math.max(completionRate, 0), 100)}%` }}
        />
      </div>

      {metrics.status_distribution && Object.keys(metrics.status_distribution).length > 0 && (
        <div className="status-distribution">
          <span className="distribution-title">Distribución por Estado:</span>
          <div className="distribution-tags">
            {Object.entries(metrics.status_distribution).map(([statusName, count]) => (
              <span key={statusName} className="status-tag">
                {statusName}: <strong>{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
