@echo off
REM build.bat — Build de um clique do Gerador de Certificados
REM Requer: Python 3.11 no PATH, pip install -r requirements-dev.txt

echo.
echo =========================================
echo   Gerador de Certificados — Build
echo =========================================
echo.

REM Verifica Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python nao encontrado no PATH.
    echo Instale Python 3.11 em: https://python.org/downloads
    pause
    exit /b 1
)

REM Instala dependências
echo [1/4] Instalando dependencias...
python -m pip install -r requirements-dev.txt --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)

REM Gera ícone
echo [2/4] Gerando icone...
python scripts/gerar_icone.py

REM Executa testes
echo [3/4] Executando testes...
python -m pytest tests/ --cov=app -q --tb=short
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO: Testes falharam. Build cancelado.
    echo Corrija os erros antes de gerar o executavel.
    pause
    exit /b 1
)

REM Gera o executável
echo [4/4] Compilando executavel...
python -m PyInstaller build.spec --clean --noconfirm
IF %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha na compilacao PyInstaller.
    pause
    exit /b 1
)

echo.
echo =========================================
echo   Build concluido com sucesso!
echo   Executavel: dist\Gerador_Certificados.exe
echo =========================================
echo.
pause
