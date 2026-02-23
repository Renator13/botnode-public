#!/usr/bin/env python3
"""
Extensiones para el backend de BotNode para soportar 38 skills dinámicos
VERSIÓN FIXED v2 con soporte para API keys internas
"""

import os
import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
import httpx
from datetime import datetime

# Router para endpoints de skills
skills_router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

# Configuración de entorno
IS_DOCKER = os.getenv("IS_DOCKER", "false").lower() == "true"
BASE_HOST = "localhost" if not IS_DOCKER else "skill"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "botnode-internal-key")

# Registro dinámico de skills
SKILL_REGISTRY: Dict[str, Dict] = {}
SKILL_CATEGORIES: Dict[str, List[str]] = {}

def initialize_skill_registry():
    """Inicializar registro de skills con los 38 skills disponibles"""
    print("🚀 Inicializando registro de skills...")
    print(f"🔧 Modo: {'Docker' if IS_DOCKER else 'Desarrollo local'}")
    print(f"🔑 Internal API Key: {INTERNAL_API_KEY[:10]}...")
    
    # Skills core (primeros 10) - CONFIGURACIÓN PARA DESARROLLO LOCAL
    core_skills = [
        {
            "id": "csv_parser",
            "name": "CSV Parser",
            "description": "Parse and process CSV files with various options",
            "category": "data_processing",
            "price_tck": 0.3,
            "docker_service": "skill-csv-parser",
            "endpoint": f"http://localhost:8001" if not IS_DOCKER else "http://skill-csv-parser:8080",
            "public_endpoint": "/skill/csv-parser",
            "port": 8001,
            "status": "discovered",
            "requires_internal_key": True
        },
        {
            "id": "pdf_reader",
            "name": "PDF Reader",
            "description": "Extract text and metadata from PDF documents",
            "category": "data_processing",
            "price_tck": 0.4,
            "docker_service": "skill-pdf-reader",
            "endpoint": f"http://localhost:8002" if not IS_DOCKER else "http://skill-pdf-reader:8080",
            "public_endpoint": "/skill/pdf-reader",
            "port": 8002,
            "status": "discovered",
            "requires_internal_key": True
        },
        {
            "id": "google_search",
            "name": "Google Search",
            "description": "Search the web using Google API",
            "category": "web_research",
            "price_tck": 0.5,
            "docker_service": "skill-google-search",
            "endpoint": f"http://localhost:8003" if not IS_DOCKER else "http://skill-google-search:8080",
            "public_endpoint": "/skill/google-search",
            "port": 8003,
            "status": "discovered",
            "requires_internal_key": True
        },
        {
            "id": "sentiment_analyzer",
            "name": "Sentiment Analyzer",
            "description": "Analyze sentiment in text content",
            "category": "analysis",
            "price_tck": 0.6,
            "docker_service": "skill-sentiment-analyzer",
            "endpoint": f"http://localhost:8004" if not IS_DOCKER else "http://skill-sentiment-analyzer:8080",
            "public_endpoint": "/skill/sentiment-analyzer",
            "port": 8004,
            "status": "discovered",
            "requires_internal_key": True
        },
        {
            "id": "code_reviewer",
            "name": "Code Reviewer",
            "description": "Review and analyze code quality",
            "category": "analysis",
            "price_tck": 0.7,
            "docker_service": "skill-code-reviewer",
            "endpoint": f"http://localhost:8005" if not IS_DOCKER else "http://skill-code-reviewer:8080",
            "public_endpoint": "/skill/code-reviewer",
            "port": 8005,
            "status": "discovered",
            "requires_internal_key": True
        }
    ]
    
    # Agregar al registro
    for skill in core_skills:
        SKILL_REGISTRY[skill["id"]] = skill
        
        # Agrupar por categoría
        category = skill["category"]
        if category not in SKILL_CATEGORIES:
            SKILL_CATEGORIES[category] = []
        SKILL_CATEGORIES[category].append(skill["id"])
    
    print(f"✅ Registro inicializado: {len(SKILL_REGISTRY)} skills")
    print(f"✅ Categorías: {list(SKILL_CATEGORIES.keys())}")
    
    # Mostrar endpoints configurados
    for skill_id, skill in SKILL_REGISTRY.items():
        print(f"  • {skill_id}: {skill['endpoint']}")

async def check_skill_health(skill_id: str) -> bool:
    """Verificar salud de un skill"""
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        return False
    
    try:
        # Usar httpx asíncrono
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{skill['endpoint']}/healthz")
            return response.status_code == 200
    except Exception as e:
        print(f"  ⚠️  Health check failed for {skill_id}: {e}")
        return False

@skills_router.get("")
async def list_skills(category: Optional[str] = None, available_only: bool = False):
    """Listar todos los skills disponibles"""
    skills_list = []
    
    for skill_id, skill in SKILL_REGISTRY.items():
        # Filtrar por categoría si se especifica
        if category and skill["category"] != category:
            continue
        
        skill_copy = skill.copy()
        
        # Verificar disponibilidad si se solicita
        skill_copy["available"] = await check_skill_health(skill_id)
        if available_only and not skill_copy["available"]:
            continue
        
        skills_list.append(skill_copy)
    
    return {
        "skills": skills_list,
        "count": len(skills_list),
        "categories": list(SKILL_CATEGORIES.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@skills_router.get("/{skill_id}")
async def get_skill_info(skill_id: str):
    """Obtener información detallada de un skill"""
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Agregar información de disponibilidad
    skill_info = skill.copy()
    skill_info["available"] = await check_skill_health(skill_id)
    
    return skill_info

@skills_router.get("/{skill_id}/health")
async def get_skill_health(skill_id: str):
    """Obtener estado de salud de un skill"""
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    is_healthy = await check_skill_health(skill_id)
    
    return {
        "skill_id": skill_id,
        "skill_name": skill["name"],
        "healthy": is_healthy,
        "endpoint": skill["endpoint"],
        "checked_at": datetime.utcnow().isoformat()
    }

@skills_router.post("/{skill_id}/execute")
async def execute_skill(skill_id: str, input_data: dict):
    """Ejecutar un skill específico"""
    skill = SKILL_REGISTRY.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Verificar que el skill esté disponible
    if not await check_skill_health(skill_id):
        raise HTTPException(status_code=503, detail="Skill not available")
    
    try:
        # Headers para el skill
        headers = {
            "Content-Type": "application/json"
        }
        
        # Agregar API key interna si el skill lo requiere
        if skill.get("requires_internal_key", False):
            headers["X-INTERNAL-API-KEY"] = INTERNAL_API_KEY
        
        # Ejecutar skill
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{skill['endpoint']}/run",
                json=input_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "skill_id": skill_id,
                    "skill_name": skill["name"],
                    "result": response.json(),
                    "executed_at": datetime.utcnow().isoformat(),
                    "price_tck": skill["price_tck"]
                }
            else:
                return {
                    "success": False,
                    "skill_id": skill_id,
                    "error": f"Skill returned status {response.status_code}",
                    "details": response.text,
                    "executed_at": datetime.utcnow().isoformat()
                }
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Skill timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing skill: {str(e)}")

@skills_router.get("/health/summary")
async def skills_health_summary():
    """Resumen de salud de todos los skills"""
    health_status = []
    
    for skill_id, skill in SKILL_REGISTRY.items():
        is_healthy = await check_skill_health(skill_id)
        health_status.append({
            "skill_id": skill_id,
            "skill_name": skill["name"],
            "healthy": is_healthy,
            "category": skill["category"],
            "endpoint": skill["endpoint"]
        })
    
    healthy_count = sum(1 for s in health_status if s["healthy"])
    total_count = len(health_status)
    
    return {
        "total_skills": total_count,
        "healthy_skills": healthy_count,
        "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
        "health_status": health_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# Inicializar registro al importar
initialize_skill_registry()

# Función para integrar con main.py
def add_skill_routes_to_app(app):
    """Agregar rutas de skills a la aplicación FastAPI"""
    app.include_router(skills_router)
    print("✅ Rutas de skills agregadas al backend")
    
    # También agregar endpoint de health extendido
    @app.get("/health/extended")
    async def extended_health():
        """Health check extendido con skills"""
        base_health = {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
        
        # Verificar skills
        skills_health = await skills_health_summary()
        
        return {
            **base_health,
            "skills": skills_health
        }

if __name__ == "__main__":
    # Prueba básica del módulo
    import asyncio
    
    async def test():
        print("🧪 Probando módulo de skills...")
        
        # Inicializar registro
        initialize_skill_registry()
        
        print(f"Skills registrados: {len(SKILL_REGISTRY)}")
        print(f"Categorías: {list(SKILL_CATEGORIES.keys())}")
        
        # Simular health check
        for skill_id in list(SKILL_REGISTRY.keys())[:3]:
            healthy = await check_skill_health(skill_id)
            print(f"  {skill_id}: {'✅' if healthy else '❌'}")
    
    asyncio.run(test())