@echo off
SETLOCAL

REM Check if Docker is running
docker info > nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM Create .env if it doesn't exist
IF NOT EXIST .env (
    echo Creating .env file from template...
    copy .env.example .env
)

REM Start Docker containers
echo Starting Docker containers...
docker-compose up -d

REM Wait for services to be ready
echo Waiting for services to be ready...
SET MAX_RETRIES=30
SET RETRY_COUNT=0

REM TODO: clear kafka topics before and after running tests
:CHECK_KAFKA
echo Checking Kafka...
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9092 >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    SET /A RETRY_COUNT+=1
    IF %RETRY_COUNT% GEQ %MAX_RETRIES% (
        echo Timeout waiting for Kafka after 60 seconds
        goto CLEANUP
    )
    echo Waiting for Kafka... Attempt %RETRY_COUNT% of %MAX_RETRIES%
    timeout /t 2 /nobreak > NUL
    goto CHECK_KAFKA
)

SET RETRY_COUNT=0

:CHECK_REDIS
echo Checking Redis...
docker-compose exec redis redis-cli ping >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    SET /A RETRY_COUNT+=1
    IF %RETRY_COUNT% GEQ %MAX_RETRIES% (
        echo Timeout waiting for Redis after 60 seconds
        goto CLEANUP
    )
    echo Waiting for Redis... Attempt %RETRY_COUNT% of %MAX_RETRIES%
    timeout /t 2 /nobreak > NUL
    goto CHECK_REDIS
)

echo All services are ready!

REM Setup virtual environment if it doesn't exist
IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate
)

REM Run util tests
echo Running util tests...
pytest -v -s src/backend/test/util/
SET UTIL_TEST_RESULT=%ERRORLEVEL%

REM Run server tests
echo Running server tests...
pytest -v -s src/backend/test/server/
SET SERVER_TEST_RESULT=%ERRORLEVEL%

REM Run worker tests
echo Running worker tests...
pytest -v -s src/backend/test/worker/
SET WORKER_TEST_RESULT=%ERRORLEVEL%

:CLEANUP
REM Cleanup
echo Cleaning up...

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat

REM Stop Docker containers
echo Stopping Docker containers...
docker-compose down

IF %UTIL_TEST_RESULT% EQU 0 IF %SERVER_TEST_RESULT% EQU 0 IF %WORKER_TEST_RESULT% EQU 0 IF %E2E_TEST_RESULT% EQU 0 (
    echo All tests passed!
) ELSE (
    echo Tests failed!
    exit /b 1
)

echo Test run complete!
ENDLOCAL 