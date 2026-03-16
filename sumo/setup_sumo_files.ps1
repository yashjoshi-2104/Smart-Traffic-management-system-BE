# setup_sumo_complete.ps1
Write-Host "🚀 Complete SUMO Setup Script" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

# Check SUMO_HOME
if (-not $env:SUMO_HOME) {
    Write-Host "❌ ERROR: SUMO_HOME not set!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ SUMO_HOME: $env:SUMO_HOME`n" -ForegroundColor Green

# Navigate to sumo directory
cd sumo

# ====== STEP 1: Generate Networks ======
Write-Host "📐 STEP 1: Generating Networks..." -ForegroundColor Cyan

cd networks

Write-Host "  Creating simple_intersection.net.xml..." -ForegroundColor Yellow
netgenerate --grid --grid.number=1 --grid.length=200 --default.lanenumber=2 --output-file=simple_intersection.net.xml

Write-Host "  Creating multi_intersection.net.xml..." -ForegroundColor Yellow
netgenerate --grid --grid.number=3 --grid.length=200 --default.lanenumber=2 --output-file=multi_intersection.net.xml

Write-Host "  Creating highway_section.net.xml..." -ForegroundColor Yellow
netgenerate --grid --grid.number=1 --grid.attach-length=500 --default.lanenumber=3 --output-file=highway_section.net.xml

cd ..

# ====== STEP 2: Generate Routes ======
Write-Host "`n🚗 STEP 2: Generating Traffic Routes..." -ForegroundColor Cyan

cd routes

Write-Host "  Creating synthetic_traffic.rou.xml..." -ForegroundColor Yellow
python $env:SUMO_HOME/tools/randomTrips.py -n ../networks/simple_intersection.net.xml -r synthetic_traffic.rou.xml --begin 0 --end 3600 --period 2 --binomial 4 2>$null

Write-Host "  Creating test_heavy.rou.xml..." -ForegroundColor Yellow
python $env:SUMO_HOME/tools/randomTrips.py -n ../networks/simple_intersection.net.xml -r test_heavy.rou.xml --begin 0 --end 600 --period 1 --binomial 3 2>$null

Write-Host "  test_light.rou.xml (paste manually)" -ForegroundColor Yellow

cd ..

# ====== STEP 3: Verify Files ======
Write-Host "`n✅ STEP 3: Verification..." -ForegroundColor Cyan

$files = @(
    "networks/simple_intersection.net.xml",
    "networks/multi_intersection.net.xml", 
    "networks/highway_section.net.xml",
    "routes/synthetic_traffic.rou.xml",
    "routes/test_heavy.rou.xml",
    "additional/vtypes.xml",
    "configs/test.sumocfg",
    "configs/baseline.sumocfg",
    "configs/rl.sumocfg",
    "configs/training.sumocfg"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file (MISSING)" -ForegroundColor Red
    }
}

Write-Host "`n================================" -ForegroundColor Green
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "`nTest with:" -ForegroundColor Yellow
Write-Host "  sumo-gui -c configs/test.sumocfg" -ForegroundColor White

cd ..