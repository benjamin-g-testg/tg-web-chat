"""
ALTERNATIVA: Usar BD Local (PostgreSQL) en lugar de Jira Cloud API

Este archivo contiene fetch_metrics_bd() que lee de la BD Local.

================================================================================
CUÁNDO USAR CADA UNA:

  JIRA CLOUD (metrics_service.py - ACTUAL):
     - Datos en tiempo real
     - Cambios en Jira se reflejan automáticamente
     - Requiere token activo

  BD LOCAL (este archivo - TESTING):
     - Testing offline (sin internet)
     - ~99 issues históricos del Excel
     - No depende de Jira Cloud
     - Más rápido

================================================================================
CÓMO CAMBIAR A BD LOCAL:

  En backend/src/api/views.py, cambiar:
  
  De:
    from .metrics_service import fetch_metrics
  
  A:
    from .metrics_service_bd_local import fetch_metrics_bd as fetch_metrics

  El resto funciona igual, sin cambios.

================================================================================
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass(frozen=True)
class JiraMetrics:
    """Mismo dataclass que metrics_service.py"""
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    new: int = 0
    blocked: int = 0
    average_open_days: int = 0
    issues_found: Optional[List[Dict]] = field(default_factory=list, repr=False)
    
    def to_dict(self, include_debug: bool = False) -> Dict:
        result = {
            "total": self.total,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "new": self.new,
            "blocked": self.blocked,
            "average_open_days": self.average_open_days,
        }
        if include_debug and self.issues_found:
            result["debug_issues"] = self.issues_found
        return result


def fetch_metrics_bd(search_filter: str = "", exclude_subtasks: bool = True, debug: bool = True) -> JiraMetrics:
    """Clasifica datos de BD Local en lugar de Jira Cloud"""
    from src.database.models import JiraIssue
    from django.db.models import Q
    
    try:
        qs = JiraIssue.objects.all()
        
        if search_filter:
            qs = qs.filter(Q(summary__icontains=search_filter) | Q(status__icontains=search_filter))
        
        total = qs.count()
        
        if debug:
            print(f"BD LOCAL: Leyendo JiraIssue")
            if search_filter:
                print(f"   Filtro: {search_filter}")
            print(f"Total incidencias encontradas: {total}\n")
        
        if total == 0:
            return JiraMetrics()
        
        completed = 0
        in_progress = 0
        new_count = 0
        blocked = 0
        issues_debug = []
        
        for issue in qs:
            status_lower = issue.status.lower() if issue.status else ""
            priority_lower = (issue.priority or "").lower()
            
            # Clasificar por estado
            if any(s in status_lower for s in ['terminado', 'done', 'cerrado', 'resuelto']):
                category = "done"
                completed += 1
            elif any(s in status_lower for s in ['en curso', 'in progress', 'progreso']):
                category = "indeterminate"
                in_progress += 1
            else:
                category = "new"
                new_count += 1
            
            is_blocked = 'bloque' in status_lower or 'bloqueante' in priority_lower
            if is_blocked:
                blocked += 1
            
            if debug:
                print(f"  • {issue.key}: {issue.summary[:50]}...")
                print(f"    └─ Estado: {issue.status} | Categoría: {category}")
                if is_blocked:
                    print(f"    └─ BLOQUEADO")
                print()
            
            issues_debug.append({
                "key": issue.key,
                "summary": issue.summary,
                "status": issue.status,
                "category": category,
                "priority": issue.priority or "medium",
                "type": getattr(issue, 'issue_type', 'Unknown'),
                "blocked": is_blocked
            })
        
        return JiraMetrics(
            total=total,
            completed=completed,
            in_progress=in_progress,
            new=new_count,
            blocked=blocked,
            issues_found=issues_debug
        )
    
    except Exception as e:
        print(f"Error leyendo BD Local: {e}")
        return JiraMetrics()