# AetherOS Automated Deployment Script
# Deploys local workspace changes to the Azure VM

$ServerHost = "ather-os.de5.net"
$ServerUser = "azureuser"
$PrivateKey = "Ather-os_key.pem"
$RemoteDir = "/home/azureuser/aetheros"
$ArchiveName = "deploy.tar.gz"

Write-Host "1. Packaging workspace..." -ForegroundColor Cyan

# Create tar.gz excluding bulky, cache, and key files
tar -czf $ArchiveName `
  --exclude="node_modules" `
  --exclude="apps/web/.next" `
  --exclude="apps/web/node_modules" `
  --exclude="apps/api/venv" `
  --exclude="apps/api/__pycache__" `
  --exclude="packages/database/__pycache__" `
  --exclude="*.pem" `
  --exclude="*.pub" `
  --exclude=".git" `
  --exclude="app.zip" `
  --exclude="app_deploy.zip" `
  --exclude="uploads" `
  --exclude="tokensave" `
  --exclude=".tokensave" `
  --exclude="brain" `
  --exclude="test.tar.gz" `
  --exclude="test.zip" `
  --exclude="$ArchiveName" `
  .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to package workspace."
    exit $LASTEXITCODE
}

Write-Host "2. Uploading archive to Azure server ($ServerHost)..." -ForegroundColor Cyan
scp -i $PrivateKey -o StrictHostKeyChecking=no $ArchiveName "${ServerUser}@${ServerHost}:${RemoteDir}/"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Cleaning up local archive..." -ForegroundColor Yellow
    Remove-Item $ArchiveName -ErrorAction SilentlyContinue
    Write-Error "Failed to upload archive via SCP."
    exit $LASTEXITCODE
}

Write-Host "3. Extracting files and rebuilding containers on the server..." -ForegroundColor Cyan
# Run extraction and docker-compose up on the server
ssh -i $PrivateKey -o StrictHostKeyChecking=no "${ServerUser}@${ServerHost}" @"
cd $RemoteDir
echo 'Extracting archive...'
tar -xzf $ArchiveName
rm $ArchiveName

echo 'Rebuilding and launching containers...'
docker compose up --build -d

echo 'Pruning unused Docker images to free up space...'
docker image prune -f
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "Cleaning up local archive..." -ForegroundColor Yellow
    Remove-Item $ArchiveName -ErrorAction SilentlyContinue
    Write-Error "Remote deployment commands failed."
    exit $LASTEXITCODE
}

Write-Host "4. Cleaning up local archive..." -ForegroundColor Cyan
Remove-Item $ArchiveName -ErrorAction SilentlyContinue

Write-Host "Deployment completed successfully! 🎉" -ForegroundColor Green
