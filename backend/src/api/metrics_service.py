from dataclasses import dataclass, field
from django.conf import settings
from jira import JIRA
from typing import Optional, List, Dict

@dataclass(frozen=True)
class JiraMetrics:
    """
    Métricas de Jira basadas en categorías globales nativas.
    frozen=True + field(default_factory=...) garantiza inmutabilidad sin issues de mutabilidad.
    """
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    new: int = 0
    blocked: int = 0
    average_open_days: int = 0
    # issues_found no se envía a JSON por defecto, solo disponible en debug
    issues_found: Optional[List[Dict]] = field(default_factory=list, repr=False)
    
    def to_dict(self, include_debug: bool = False) -> Dict:
        """
        Serializa a diccionario seguro para JSON.
        Si include_debug=False, excluye issues_found para respuestas HTTP limpias.
        """
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

def fetch_metrics(search_filter: str = "", exclude_subtasks: bool = True, debug: bool = True) -> JiraMetrics:
    """
    Se conecta a la API de Jira y clasifica dinámicamente por categorías globales nativas.
    Categorías globales nativas de Jira: 'new', 'indeterminate', 'done'
    
    Args:
        search_filter: Filtro adicional por summary o status
        exclude_subtasks: Si es True, excluye subtareas del conteo
        debug: Si es True, imprime detalles de cada incidencia
    """
    try:
        jira = JIRA(
            server=settings.JIRA_SERVER,
            basic_auth=(settings.JIRA_USER, settings.JIRA_API_TOKEN)
        )
        
        # JQL mejorado: excluye subtareas por defecto
        jql = 'project = "TATC"'
        if exclude_subtasks:
            jql += ' AND type != Sub-task'
        
        if search_filter:
            jql += f' AND (summary ~ "{search_filter}" OR status ~ "{search_filter}")'
        
        if debug:
            print(f"JQL ejecutado: {jql}")
            
        issues = jira.search_issues(jql, maxResults=50)
        
        total = len(issues)
        if debug:
            print(f"Total incidencias encontradas: {total}\n")
        
        if total == 0:
            return JiraMetrics()
            
        completed = 0
        in_progress = 0
        new_count = 0
        blocked = 0
        issues_debug = []
        
        for issue in issues:
            # Obtenemos la categoría global del estado nativa desde Jira
            # Opciones nativas: 'done', 'indeterminate', 'new'
            status_category = ""
            if hasattr(issue.fields, 'status') and hasattr(issue.fields.status, 'statusCategory'):
                status_category = issue.fields.status.statusCategory.key.lower()
            
            status_name = issue.fields.status.name.lower()
            priority = issue.fields.priority.name.lower() if issue.fields.priority else ""
            
            if debug:
                print(f"  • {issue.key}: {issue.fields.summary[:50]}...")
                print(f"    └─ Estado: {issue.fields.status.name} | Categoría: {status_category} | Prioridad: {priority}")
            
            # Clasificación por categoría global (nativa de Jira)
            if status_category == "done":
                completed += 1
            elif status_category == "indeterminate":
                in_progress += 1
            elif status_category == "new":
                new_count += 1
                
            # Detecta bloqueos por campo personalizado O por texto en estado/prioridad
            is_blocked = False
            
            # Opción 1: Campo personalizado de bloqueo (si existe)
            if hasattr(issue.fields, 'customfield_blocked') and issue.fields.customfield_blocked:
                is_blocked = True
            
            # Opción 2: Busca en nombre del estado o prioridad
            if not is_blocked and ("bloque" in status_name or "bloqueante" in priority or "blocked" in status_name):
                is_blocked = True
            
            if is_blocked:
                blocked += 1
                if debug:
                    print(f"    └─ BLOQUEADO")
            
            if debug:
                print()
            
            issues_debug.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "category": status_category,
                "priority": priority,
                "type": issue.fields.issuetype.name,
                "blocked": is_blocked
            })
                
        return JiraMetrics(
            total=total,
            completed=completed,
            in_progress=in_progress,
            new=new_count,
            blocked=blocked,
            average_open_days=0,
            issues_found=issues_debug
        )
        
    except Exception as e:
        print(f"Error conectando a Jira API: {e}")
        return JiraMetrics()
