#!/usr/bin/env python3
"""
Patch para integrar el módulo de skills en el backend principal
"""

import os
import sys

# Ruta al backend
backend_dir = "/home/ubuntu/.openclaw/botnode_mvp"
main_py_path = os.path.join(backend_dir, "main.py")

# Leer el archivo main.py actual
with open(main_py_path, 'r') as f:
    content = f.read()

# Buscar donde agregar las importaciones del módulo de skills
# Después de las otras importaciones pero antes de crear la app

# Encontrar la línea donde se crea la app FastAPI
app_creation_line = "app = FastAPI(title=\"BotNode.io Core Engine\")"

if app_creation_line in content:
    # Dividir el contenido
    parts = content.split(app_creation_line)
    
    # Agregar importación del módulo de skills antes de crear la app
    import_statement = """# Import skill extensions
from backend_skill_extensions import add_skill_routes_to_app
"""
    
    # Reconstruir el contenido
    new_content = parts[0] + import_statement + app_creation_line + parts[1]
    
    # Ahora encontrar donde agregar las rutas después de crear la app
    # Buscar después de @app.get("/health")
    health_route = '@app.get("/health")'
    if health_route in new_content:
        parts2 = new_content.split(health_route)
        
        # Agregar inicialización de skills después de crear la app pero antes de las rutas
        skill_init = """
# Initialize and add skill routes
add_skill_routes_to_app(app)
"""
        
        # Reconstruir
        final_content = parts2[0] + skill_init + health_route + parts2[1]
        
        # Guardar el archivo modificado
        backup_path = main_py_path + ".backup"
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"✅ Backup creado: {backup_path}")
        
        with open(main_py_path, 'w') as f:
            f.write(final_content)
        print(f"✅ main.py actualizado con módulo de skills")
        
        # También copiar el módulo de skills al directorio del backend
        import shutil
        skill_module_src = "/home/ubuntu/.openclaw/workspace/botnode-platform/backend_skill_extensions.py"
        skill_module_dst = os.path.join(backend_dir, "backend_skill_extensions.py")
        shutil.copy2(skill_module_src, skill_module_dst)
        print(f"✅ Módulo de skills copiado a: {skill_module_dst}")
        
    else:
        print("❌ No se encontró la ruta /health")
        sys.exit(1)
else:
    print("❌ No se encontró la creación de la app FastAPI")
    sys.exit(1)

print("\n🎯 Patch aplicado exitosamente")
print("El backend ahora incluye:")
print("  • /api/v1/skills - Listar todos los skills")
print("  • /api/v1/skills/{id} - Info de skill específico")
print("  • /api/v1/skills/{id}/execute - Ejecutar skill")
print("  • /api/v1/skills/health/summary - Resumen de salud")
print("  • /health/extended - Health check extendido con skills")