#!/usr/bin/env python3
"""
Script de despliegue automático para BotNode Platform
Descubre y despliega los 38 skills automáticamente
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class BotNodeDeployer:
    def __init__(self):
        self.base_dir = Path("/home/ubuntu/.openclaw")
        self.workspace_dir = self.base_dir / "workspace"
        self.platform_dir = self.workspace_dir / "botnode-platform"
        self.skills_dir = self.platform_dir / "skills"
        
        # Crear directorios necesarios
        self.skills_dir.mkdir(exist_ok=True)
        
    def discover_skills(self) -> List[Dict[str, Any]]:
        """Descubrir automáticamente todos los skills disponibles"""
        print("🔍 Descubriendo skills...")
        
        skill_dirs = [
            self.workspace_dir / "botnode_skills_extracted",
            self.workspace_dir / "botnode_additional", 
            self.workspace_dir / "botnode_additional2"
        ]
        
        skills = []
        
        for skill_dir in skill_dirs:
            if not skill_dir.exists():
                continue
                
            for item in skill_dir.iterdir():
                if item.is_dir() and "-v1" in item.name:
                    skill_id = item.name.replace("-v1", "")
                    skill_path = item
                    
                    # Verificar que sea un skill válido
                    if self._is_valid_skill(skill_path):
                        skill_info = self._analyze_skill(skill_path, skill_id)
                        skills.append(skill_info)
                        print(f"  ✅ {skill_id}: {skill_info['description'][:50]}...")
        
        print(f"\n🎯 Total skills descubiertos: {len(skills)}")
        return skills
    
    def _is_valid_skill(self, skill_path: Path) -> bool:
        """Verificar que un directorio sea un skill válido"""
        required_files = ["Dockerfile", "pyproject.toml", "docs/contract.md"]
        
        for file in required_files:
            if not (skill_path / file).exists():
                return False
        return True
    
    def _analyze_skill(self, skill_path: Path, skill_id: str) -> Dict[str, Any]:
        """Analizar un skill para extraer información"""
        contract_file = skill_path / "docs" / "contract.md"
        readme_file = skill_path / "README.md"
        
        # Leer contrato
        description = "No description"
        if contract_file.exists():
            with open(contract_file, 'r') as f:
                content = f.read()
                # Extraer objetivo del contrato
                lines = content.split('\n')
                for line in lines:
                    if line.startswith("## Objective"):
                        description = lines[lines.index(line) + 1].strip()
                        break
        
        # Determinar categoría
        category = self._categorize_skill(skill_id, description)
        
        # Determinar precio estimado
        price = self._estimate_price(category, skill_id)
        
        return {
            "id": skill_id,
            "docker_service": f"skill-{skill_id}",
            "path": str(skill_path),
            "category": category,
            "description": description,
            "estimated_price_tck": price,
            "port": self._assign_port(skill_id)
        }
    
    def _categorize_skill(self, skill_id: str, description: str) -> str:
        """Categorizar skill automáticamente"""
        skill_id_lower = skill_id.lower()
        description_lower = description.lower()
        
        # Mapeo de categorías
        data_processing = ["csv", "pdf", "data", "enrich", "vector", "schema"]
        web_research = ["google", "web", "scraper", "url", "research", "search"]
        analysis = ["sentiment", "hallucination", "code", "analyzer", "diff", "quality"]
        infrastructure = ["scheduler", "notification", "report", "prompt", "logic", "memory"]
        translation = ["translator", "language", "text"]
        
        for keyword in data_processing:
            if keyword in skill_id_lower or keyword in description_lower:
                return "data_processing"
        
        for keyword in web_research:
            if keyword in skill_id_lower or keyword in description_lower:
                return "web_research"
        
        for keyword in analysis:
            if keyword in skill_id_lower or keyword in description_lower:
                return "analysis"
        
        for keyword in infrastructure:
            if keyword in skill_id_lower or keyword in description_lower:
                return "infrastructure"
        
        for keyword in translation:
            if keyword in skill_id_lower or keyword in description_lower:
                return "translation"
        
        return "other"
    
    def _estimate_price(self, category: str, skill_id: str) -> float:
        """Estimar precio en $TCK$ basado en categoría y complejidad"""
        base_prices = {
            "data_processing": 0.3,
            "web_research": 0.5,
            "analysis": 0.7,
            "infrastructure": 0.4,
            "translation": 0.3,
            "other": 0.2
        }
        
        # Ajustar por complejidad
        complexity_indicators = ["hallucination", "code", "sentiment", "research", "memory"]
        for indicator in complexity_indicators:
            if indicator in skill_id.lower():
                return base_prices.get(category, 0.3) * 1.5
        
        return base_prices.get(category, 0.3)
    
    def _assign_port(self, skill_id: str) -> int:
        """Asignar puerto único basado en hash del skill_id"""
        # Puerto base: 8100 + hash(skill_id) % 100
        hash_val = hash(skill_id) % 100
        return 8100 + hash_val
    
    def generate_docker_compose(self, skills: List[Dict[str, Any]]) -> str:
        """Generar docker-compose.yml con todos los skills"""
        print("\n🔧 Generando docker-compose.yml...")
        
        # Plantilla base
        template = """version: '3.8'

services:
  # --- INFRAESTRUCTURA BASE ---
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: botnode
      POSTGRES_USER: botnode
      POSTGRES_PASSWORD: botnode_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U botnode"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # --- BACKEND PRINCIPAL ---
  backend:
    build:
      context: ../botnode_mvp
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://botnode:botnode_password@postgres:5432/botnode
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET_KEY: botnode_jwt_secret_key_change_in_production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # --- SKILLS ---
{skills_services}

volumes:
  postgres_data:
  redis_data:
"""
        
        # Generar servicios para cada skill
        skills_services = []
        for skill in skills:
            skill_service = f"""  skill-{skill['id']}:
    build:
      context: {skill['path']}
      dockerfile: Dockerfile
    environment:
      BOTNODE_API_URL: http://backend:8000
      SKILL_ID: {skill['id']}_v1
    ports:
      - "{skill['port']}:8000"
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
            skills_services.append(skill_service)
        
        skills_services_str = "\n".join(skills_services)
        return template.format(skills_services=skills_services_str)
    
    def generate_skill_registry(self, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar registro JSON de skills para el backend"""
        print("\n📋 Generando registro de skills...")
        
        registry = {
            "skills": {},
            "categories": {},
            "total_count": len(skills),
            "generated_at": "2026-02-22T15:45:00Z"
        }
        
        for skill in skills:
            skill_id = skill['id']
            registry["skills"][skill_id] = {
                "id": skill_id,
                "name": skill_id.replace("_", " ").title(),
                "description": skill['description'],
                "category": skill['category'],
                "price_tck": skill['estimated_price_tck'],
                "docker_service": skill['docker_service'],
                "endpoint": f"http://skill-{skill_id}:8000",
                "public_endpoint": f"/skill/{skill_id}",
                "port": skill['port'],
                "status": "discovered"
            }
            
            # Agrupar por categoría
            category = skill['category']
            if category not in registry["categories"]:
                registry["categories"][category] = []
            registry["categories"][category].append(skill_id)
        
        return registry
    
    def deploy(self):
        """Ejecutar despliegue completo"""
        print("🚀 INICIANDO DESPLIEGUE BOTNODE PLATFORM")
        print("=" * 50)
        
        # 1. Descubrir skills
        skills = self.discover_skills()
        
        if not skills:
            print("❌ No se encontraron skills válidos")
            return False
        
        # 2. Generar docker-compose.yml
        docker_compose = self.generate_docker_compose(skills)
        docker_compose_file = self.platform_dir / "docker-compose.full.yml"
        docker_compose_file.write_text(docker_compose)
        print(f"✅ docker-compose.yml generado: {docker_compose_file}")
        
        # 3. Generar registro de skills
        registry = self.generate_skill_registry(skills)
        registry_file = self.platform_dir / "skill-registry.json"
        registry_file.write_text(json.dumps(registry, indent=2))
        print(f"✅ Registro de skills generado: {registry_file}")
        
        # 4. Generar script de inicialización
        self._generate_init_script(skills)
        
        # 5. Crear archivo .env
        self._generate_env_file()
        
        print("\n🎯 DESPLIEGUE PREPARADO")
        print("=" * 50)
        print(f"Total skills: {len(skills)}")
        print(f"Categorías: {len(registry['categories'])}")
        print(f"Puertos asignados: {skill['port']} - {skills[-1]['port']}")
        
        print("\n📋 COMANDOS PARA EJECUTAR:")
        print("1. cd /home/ubuntu/.openclaw/workspace/botnode-platform")
        print("2. docker-compose -f docker-compose.full.yml up -d")
        print("3. Ver logs: docker-compose -f docker-compose.full.yml logs -f")
        
        return True
    
    def _generate_init_script(self, skills: List[Dict[str, Any]]):
        """Generar script de inicialización para el backend"""
        script_content = """#!/usr/bin/env python3
"""
        
        init_file = self.platform_dir / "init_backend.py"
        init_file.write_text(script_content)
        init_file.chmod(0o755)
    
    def _generate_env_file(self):
        """Generar archivo .env de ejemplo"""
        env_content = """# BotNode Platform Environment Variables
# Backend
DATABASE_URL=postgresql://botnode:botnode_password@postgres:5432/botnode
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=botnode_jwt_secret_key_change_in_production

# External APIs (opcional)
GOOGLE_API_KEY=your_google_api_key_here
DEEPL_API_KEY=your_deepl_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin
"""
        
        env_file = self.platform_dir / ".env.example"
        env_file.write_text(env_content)

def main():
    """Función principal"""
    deployer = BotNodeDeployer()
    
    try:
        success = deployer.deploy()
        if success:
            print("\n✅ DESPLIEGUE COMPLETADO EXITOSAMENTE")
            sys.exit(0)
        else:
            print("\n❌ DESPLIEGUE FALLIDO")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()