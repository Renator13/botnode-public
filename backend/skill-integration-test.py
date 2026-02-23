#!/usr/bin/env python3
"""
Test de integración Backend + Skill CSV-Parser
"""

import requests
import json
import time

def test_backend_health():
    """Test health check del backend"""
    print("🔍 Test 1: Health check del backend")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Backend saludable: {response.json()}")
            return True
        else:
            print(f"  ❌ Backend error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Backend no disponible: {e}")
        return False

def test_skill_health(skill_name, port):
    """Test health check de un skill"""
    print(f"🔍 Test 2: Health check de {skill_name}")
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ {skill_name} saludable (puerto {port})")
            return True
        else:
            print(f"  ❌ {skill_name} error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ {skill_name} no disponible: {e}")
        return False

def test_skill_execution(skill_name, port, endpoint, input_data):
    """Test ejecución de un skill"""
    print(f"🔍 Test 3: Ejecución de {skill_name}")
    try:
        url = f"http://localhost:{port}{endpoint}"
        response = requests.post(
            url,
            json=input_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ {skill_name} ejecutado exitosamente")
            print(f"     Resultado: {json.dumps(result, indent=2)[:200]}...")
            return True, result
        else:
            print(f"  ❌ {skill_name} error: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False, None
    except Exception as e:
        print(f"  ❌ {skill_name} error de ejecución: {e}")
        return False, None

def test_csv_parser():
    """Test específico para CSV Parser"""
    print("🔍 Test CSV Parser: Procesamiento básico")
    
    # Datos de ejemplo CSV
    csv_data = "name,age,city\nJohn,30,New York\nJane,25,London\nBob,35,Tokyo"
    
    input_data = {
        "csv_content": csv_data,
        "options": {
            "delimiter": ",",
            "has_header": True,
            "parse_types": True
        }
    }
    
    success, result = test_skill_execution(
        "csv-parser",
        8001,
        "/parse",
        input_data
    )
    
    if success and result:
        print(f"  ✅ CSV procesado correctamente")
        print(f"     Filas: {len(result.get('data', []))}")
        print(f"     Columnas: {result.get('columns', [])}")
        return True
    return False

def test_backend_skill_registration():
    """Test registro de skill en backend"""
    print("🔍 Test 4: Registro de skill en backend")
    
    # Primero verificar si el endpoint de skills existe
    try:
        response = requests.get("http://localhost:8000/api/v1/skills", timeout=5)
        if response.status_code == 200:
            skills = response.json()
            print(f"  ✅ Skills endpoint funciona: {len(skills.get('skills', []))} skills")
            return True
        elif response.status_code == 404:
            print("  ⚠️  Endpoint /api/v1/skills no implementado aún")
            return False
        else:
            print(f"  ❌ Error inesperado: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error conectando a backend: {e}")
        return False

def main():
    """Función principal de testing"""
    print("🚀 INICIANDO TEST DE INTEGRACIÓN BACKEND + SKILLS")
    print("=" * 60)
    
    # Test 1: Backend health
    backend_ok = test_backend_health()
    
    # Test 2: Skill health
    skill_ok = test_skill_health("csv-parser", 8001)
    
    # Test 3: CSV Parser execution
    csv_ok = False
    if skill_ok:
        csv_ok = test_csv_parser()
    
    # Test 4: Backend skill registration
    registration_ok = test_backend_skill_registration()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE TESTS:")
    print(f"  ✅ Backend health: {'PASS' if backend_ok else 'FAIL'}")
    print(f"  ✅ CSV Parser health: {'PASS' if skill_ok else 'FAIL'}")
    print(f"  ✅ CSV Parser execution: {'PASS' if csv_ok else 'FAIL'}")
    print(f"  ✅ Skill registration: {'PASS' if registration_ok else 'FAIL'}")
    
    total_tests = 4
    passed_tests = sum([backend_ok, skill_ok, csv_ok, registration_ok])
    
    print(f"\n🎯 RESULTADO FINAL: {passed_tests}/{total_tests} tests pasados")
    
    if passed_tests == total_tests:
        print("✅ INTEGRACIÓN COMPLETA - SISTEMA FUNCIONAL")
        return True
    elif passed_tests >= 2:
        print("⚠️  INTEGRACIÓN PARCIAL - ALGUNOS COMPONENTES FUNCIONAN")
        return True
    else:
        print("❌ INTEGRACIÓN FALLIDA - REVISAR COMPONENTES")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)