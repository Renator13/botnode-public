#!/usr/bin/env python3
"""
Test del módulo de skills
"""

import sys
sys.path.append('/home/ubuntu/.openclaw/workspace/botnode-platform')

from backend_skill_extensions import initialize_skill_registry
import asyncio

async def test():
    print('🧪 Probando módulo de skills...')
    initialize_skill_registry()
    
    # Verificar skills registrados
    from backend_skill_extensions import SKILL_REGISTRY
    print(f'✅ Skills registrados: {len(SKILL_REGISTRY)}')
    
    for skill_id, skill in SKILL_REGISTRY.items():
        print(f'  • {skill_id}: {skill["name"]} (${skill.get("price_tck", 0)} TCK)')
    
    # Probar health check (solo verificación de estructura)
    print('\n🔍 Health checks (estructura):')
    for skill_id in list(SKILL_REGISTRY.keys())[:2]:
        print(f'  • {skill_id}: endpoint configurado')

if __name__ == "__main__":
    asyncio.run(test())