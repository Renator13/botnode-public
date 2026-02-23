#!/usr/bin/env python3
"""
Extensiones para el backend principal de BotNode
Agrega soporte para 38 skills dinámicos
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime, timedelta

class SkillRegistry:
    """Registro dinámico de skills"""
    
    def __init__(self, registry_file: str = None):
        self.registry_file = registry_file or "/app/skill-registry.json"
        self.skills: Dict[str, Dict] = {}
        self.categories: Dict[str, List[str]] = {}
        self.load_registry()
    
    def load_registry(self):
        """Cargar registro desde archivo JSON"""
        try:
            if os.path.exists(self.registry_file):
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    self.skills = data.get('skills', {})
                    self.categories = data.get('categories', {})
                print(f"✅ Registro cargado: {len(self.skills)} skills")
            else:
                print("⚠️  Archivo de registro no encontrado, usando registro vacío")
        except Exception as e:
            print(f"❌ Error cargando registro: {e}")
            self.skills = {}
            self.categories = {}
    
    def get_skill(self, skill_id: str) -> Optional[Dict]:
        """Obtener información de un skill"""
        return self.skills.get(skill_id)
    
    def list_skills(self, category: str = None) -> List[Dict]:
        """Listar skills, opcionalmente filtrados por categoría"""
        if category:
            skill_ids = self.categories.get(category, [])
            return [self.skills.get(sid) for sid in skill_ids if sid in self.skills]
        return list(self.skills.values())
    
    def get_categories(self) -> List[str]:
        """Obtener lista de categorías"""
        return list(self.categories.keys())
    
    def skill_health_check(self, skill_id: str) -> bool:
        """Verificar salud de un skill"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        try:
            endpoint = skill.get('endpoint', f'http://skill-{skill_id}:8000')
            health_url = f"{endpoint}/health"
            
            # Timeout corto para health check
            response = httpx.get(health_url, timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_skills(self) -> List[Dict]:
        """Obtener skills disponibles (con health check)"""
        available = []
        for skill_id, skill in self.skills.items():
            skill_copy = skill.copy()
            skill_copy['available'] = self.skill_health_check(skill_id)
            available.append(skill_copy)
        return available


class SkillOrchestrator:
    """Orquestador para ejecutar skills"""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def execute_skill(self, skill_id: str, input_data: Dict, api_key: str = None) -> Dict:
        """Ejecutar un skill con datos de entrada"""
        skill = self.registry.get_skill(skill_id)
        if not skill:
            return {"error": f"Skill '{skill_id}' no encontrado"}
        
        # Verificar que el skill esté disponible
        if not self.registry.skill_health_check(skill_id):
            return {"error": f"Skill '{skill_id}' no disponible"}
        
        try:
            endpoint = skill.get('endpoint', f'http://skill-{skill_id}:8000')
            execute_url = f"{endpoint}/execute"
            
            # Headers
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Ejecutar skill
            response = await self.client.post(
                execute_url,
                json=input_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "skill_id": skill_id,
                    "result": response.json(),
                    "executed_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "skill_id": skill_id,
                    "error": f"Skill returned status {response.status_code}",
                    "details": response.text
                }
                
        except httpx.TimeoutException:
            return {"error": f"Skill '{skill_id}' timeout"}
        except Exception as e:
            return {"error": f"Error ejecutando skill: {str(e)}"}
    
    async def batch_execute(self, skill_requests: List[Dict]) -> List[Dict]:
        """Ejecutar múltiples skills en paralelo"""
        import asyncio
        
        tasks = []
        for req in skill_requests:
            skill_id = req.get('skill_id')
            input_data = req.get('input', {})
            api_key = req.get('api_key')
            
            task = self.execute_skill(skill_id, input_data, api_key)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "success": False,
                    "skill_id": skill_requests[i].get('skill_id'),
                    "error": str(result)
                })
            else:
                processed.append(result)
        
        return processed


class PricingEngine:
    """Motor de precios para skills"""
    
    def __init__(self, base_price: float = 0.1):
        self.base_price = base_price
        self.multipliers = {
            "data_processing": 1.0,
            "web_research": 1.5,
            "analysis": 2.0,
            "infrastructure": 1.2,
            "translation": 1.0,
            "other": 1.0
        }
    
    def calculate_price(self, skill_id: str, input_complexity: str = "medium") -> float:
        """Calcular precio para un skill"""
        skill = SkillRegistry().get_skill(skill_id)
        if not skill:
            return self.base_price
        
        # Precio base del skill
        base = skill.get('price_tck', self.base_price)
        
        # Multiplicador por categoría
        category = skill.get('category', 'other')
        category_mult = self.multipliers.get(category, 1.0)
        
        # Multiplicador por complejidad de entrada
        complexity_mult = {
            "simple": 0.7,
            "medium": 1.0,
            "complex": 1.5,
            "very_complex": 2.0
        }.get(input_complexity, 1.0)
        
        # Calcular precio final
        price = base * category_mult * complexity_mult
        
        # Redondear a 2 decimales
        return round(price, 2)
    
    def estimate_batch_price(self, skill_requests: List[Dict]) -> float:
        """Estimar precio para un batch de ejecuciones"""
        total = 0.0
        for req in skill_requests:
            skill_id = req.get('skill_id')
            complexity = req.get('complexity', 'medium')
            price = self.calculate_price(skill_id, complexity)
            total += price
        
        return round(total, 2)


# --- FastAPI Endpoints para integrar en main.py ---

def add_skill_endpoints(app, registry: SkillRegistry, orchestrator: SkillOrchestrator, pricing: PricingEngine):
    """Agregar endpoints de skills a la app FastAPI"""
    
    @app.get("/api/v1/skills")
    async def list_all_skills(category: str = None, available_only: bool = False):
        """Listar todos los skills disponibles"""
        if category:
            skills = registry.list_skills(category)
        else:
            skills = registry.list_skills()
        
        if available_only:
            skills = [s for s in skills if registry.skill_health_check(s['id'])]
        
        return {
            "skills": skills,
            "count": len(skills),
            "categories": registry.get_categories()
        }
    
    @app.get("/api/v1/skills/{skill_id}")
    async def get_skill_info(skill_id: str):
        """Obtener información detallada de un skill"""
        skill = registry.get_skill(skill_id)
        if not skill:
            return {"error": "Skill not found"}, 404
        
        # Agregar información de disponibilidad
        skill_info = skill.copy()
        skill_info['available'] = registry.skill_health_check(skill_id)
        skill_info['estimated_price'] = pricing.calculate_price(skill_id)
        
        return skill_info
    
    @app.post("/api/v1/skills/{skill_id}/execute")
    async def execute_skill_endpoint(skill_id: str, input_data: dict, api_key: str = None):
        """Ejecutar un skill específico"""
        result = await orchestrator.execute_skill(skill_id, input_data, api_key)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}, 400
        
        return result
    
    @app.post("/api/v1/skills/batch-execute")
    async def batch_execute_endpoint(requests: list):
        """Ejecutar múltiples skills en batch"""
        if len(requests) > 10:  # Límite por seguridad
            return {"error": "Maximum 10 skills per batch"}, 400
        
        results = await orchestrator.batch_execute(requests)
        
        # Calcular precio total
        total_price = pricing.estimate_batch_price(requests)
        
        return {
            "results": results,
            "total_price_tck": total_price,
            "count": len(results)
        }
    
    @app.get("/api/v1/skills/{skill_id}/price")
    async def get_skill_price(skill_id: str, complexity: str = "medium"):
        """Obtener precio estimado para un skill"""
        skill = registry.get_skill(skill_id)
        if not skill:
            return {"error": "Skill not found"}, 404
        
        price = pricing.calculate_price(skill_id, complexity)
        
        return {
            "skill_id": skill_id,
            "skill_name": skill.get('name', skill_id),
            "complexity": complexity,
            "price_tck": price,
            "category": skill.get('category', 'unknown')
        }
    
    @app.get("/api/v1/health/skills")
    async def skills_health_check():
        """Health check para todos los skills"""
        skills = registry.list_skills()
        health_status = []
        
        for skill in skills:
            skill_id = skill['id']
            is_healthy = registry.skill_health_check(skill_id)
            health_status.append({
                "skill_id": skill_id,
                "available": is_healthy,
                "endpoint": skill.get('endpoint', ''),
                "category": skill.get('category', 'unknown')
            })
        
        healthy_count = sum(1 for s in health_status if s['available'])
        
        return {
            "total_skills": len(skills),
            "healthy_skills": healthy_count,
            "health_status": health_status,
            "overall_health": healthy_count / len(skills) if skills else 0
        }


# --- Script de inicialización ---

def initialize_skill_system():
    """Inicializar sistema de skills"""
    print("🚀 Inicializando sistema de skills BotNode...")
    
    # Crear registro
    registry = SkillRegistry()
    
    # Crear orquestador
    orchestrator = SkillOrchestrator(registry)
    
    # Crear motor de precios
    pricing = PricingEngine()
    
    print(f"✅ Sistema inicializado con {len(registry.skills)} skills")
    print(f"✅ Categorías disponibles: {', '.join(registry.get_categories())}")
    
    return registry, orchestrator, pricing


if __name__ == "__main__":
    # Ejecutar prueba básica
    registry, orchestrator, pricing = initialize_skill_system()
    
    # Listar skills
    print("\n📋 Skills disponibles:")
    for skill in registry.list_skills():
        print(f"  • {skill['id']}: {skill.get('description', 'No description')[:60]}...")
    
    print(f"\n🎯 Sistema listo para integrar con FastAPI")