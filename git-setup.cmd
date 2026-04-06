@echo off
cd /d E:\CONFIT

echo Starting git setup... > E:\CONFIT\git-log.txt

git --version >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git init >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git config user.name "OmarAhmed-123" >> E:\CONFIT\git-log.txt 2>&1
git config user.email "omar.ahmed@example.com" >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git remote remove origin 2>nul
git remote add origin https://github.com/OmarAhmed-123/CONFIT.git >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git add . >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git commit -m "Initial commit: CONFIT fashion e-commerce platform" >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

git branch -M main >> E:\CONFIT\git-log.txt 2>&1
echo. >> E:\CONFIT\git-log.txt

echo Git setup complete! >> E:\CONFIT\git-log.txt
type E:\CONFIT\git-log.txt
