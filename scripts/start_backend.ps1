# EcoCompress AI - Start Backend Service
# Runs the FastAPI application on Python 3.13 with Uvicorn

Write-Host "=============================================" -ForegroundColor Green
Write-Host " Starting EcoCompress AI Backend API Service " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

Set-Location "D:\Projects\Compression AI"
py -3.13 services/api/main.py
