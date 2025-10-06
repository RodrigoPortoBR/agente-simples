#!/usr/bin/env python3
"""
Script de Validação do Setup
Execute para verificar se tudo está configurado corretamente
"""
import os
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_mark(condition):
    return "✅" if condition else "❌"

def validate_file_structure():
    """Valida estrutura de arquivos"""
    print_header("1. Validando Estrutura de Arquivos")
    
    required_files = [
        "config.py",
        "models.py",
        "main.py",
        "requirements.txt",
        ".env",
        "agents/__init__.py",
        "agents/orchestrator_agent.py",
        "agents/sql_agent.py",
        "services/__init__.py",
        "services/memory_service.py",
        "database/supabase_schema.sql"
    ]
    
    all_ok = True
    for file_path in required_files:
        exists = Path(file_path).exists()
        print(f"{check_mark(exists)} {file_path}")
        if not exists:
            all_ok = False
    
    return all_ok

def validate_environment():
    """Valida variáveis de ambiente"""
    print_header("2. Validando Variáveis de Ambiente")
    
    required_vars = [
        "OPENAI_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY"
    ]
    
    all_ok = True
    for var in required_vars:
        value = os.getenv(var)
        exists = value is not None and len(value) > 0
        print(f"{check_mark(exists)} {var}: {'✓ Configurada' if exists else '✗ Faltando'}")
        if not exists:
            all_ok = False
    
    return all_ok

def validate_dependencies():
    """Valida dependências instaladas"""
    print_header("3. Validando Dependências")
    
    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("openai", "OpenAI"),
        ("httpx", "HTTPX")
    ]
    
    all_ok = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Execute: pip install {package}")
            all_ok = False
    
    return all_ok

def validate_imports():
    """Valida imports dos módulos"""
    print_header("4. Validando Imports dos Módulos")
    
    modules_to_test = [
        ("config", "Configurações"),
        ("models", "Modelos"),
        ("agents.orchestrator_agent", "Orchestrator Agent"),
        ("agents.sql_agent", "SQL Agent"),
        ("services.memory_service", "Memory Service")
    ]
    
    all_ok = True
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except Exception as e:
            print(f"❌ {display_name} - Erro: {str(e)}")
            all_ok = False
    
    return all_ok

def validate_config_values():
    """Valida valores de configuração"""
    print_header("5. Validando Configurações")
    
    try:
        from config import settings
        
        checks = [
            (bool(settings.OPENAI_API_KEY), "OpenAI API Key"),
            (bool(settings.SUPABASE_URL), "Supabase URL"),
            (bool(settings.SUPABASE_ANON_KEY), "Supabase Anon Key"),
            (settings.MAX_HISTORY_MESSAGES > 0, "Max History Messages"),
            (settings.CONTEXT_WINDOW_MESSAGES > 0, "Context Window Messages")
        ]
        
        all_ok = True
        for condition, name in checks:
            print(f"{check_mark(condition)} {name}")
            if not condition:
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"❌ Erro ao carregar configurações: {e}")
        return False

def print_summary(results):
    """Imprime resumo final"""
    print_header("Resumo da Validação")
    
    all_passed = all(results.values())
    
    for check_name, passed in results.items():
        print(f"{check_mark(passed)} {check_name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 SUCESSO! Tudo está configurado corretamente!")
        print("="*60)
        print("\nPróximos passos:")
        print("1. Inicie o servidor: python main.py")
        print("2. Teste o health check: curl http://localhost:8000/health")
        print("3. Veja a documentação: README.md")
    else:
        print("⚠️  ATENÇÃO! Alguns problemas foram encontrados.")
        print("="*60)
        print("\nCorreja os itens marcados com ❌ acima.")
        print("Consulte QUICK_START.md ou IMPLEMENTATION_CHECKLIST.md")
    
    return all_passed

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  Sistema de Agentes Orquestradores - Script de Validação ║
    ║                    Versão 5.0.0                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Carregar .env se existir
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env carregado\n")
    except ImportError:
        print("⚠️  python-dotenv não instalado (opcional)")
        print("   Para usar .env: pip install python-dotenv\n")
    
    # Executar validações
    results = {
        "Estrutura de Arquivos": validate_file_structure(),
        "Variáveis de Ambiente": validate_environment(),
        "Dependências": validate_dependencies(),
        "Imports dos Módulos": validate_imports(),
        "Valores de Configuração": validate_config_values()
    }
    
    # Resumo
    all_passed = print_summary(results)
    
    # Exit code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()