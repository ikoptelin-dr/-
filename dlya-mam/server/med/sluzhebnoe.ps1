# Служебный скрипт сайта for-mom.ru: start | stop | check
param([string]$cmd = 'check')
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cfg = @{}
Get-Content (Join-Path $dir 'nastrojki.txt') -Encoding UTF8 | ForEach-Object { if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$') { $cfg[$matches[1]] = $matches[2] } }
$port = if ($cfg.SITE_PORT) { [int]$cfg.SITE_PORT } else { 8081 }
$domain = if ($cfg.SITE_DOMAIN) { $cfg.SITE_DOMAIN } else { 'for-mom.ru' }
$serverIp = '178.49.193.175'
function Ok($t) { Write-Host "[OK] $t" -ForegroundColor Green }
function Bad($t) { Write-Host "[XX] $t" -ForegroundColor Red }
function Listening { [bool](Get-NetTCPConnection -LocalPort $port -State Listen) }

switch ($cmd) {
  'start' {
    if (Listening) { Ok "Сайт уже работает: http://localhost:$port"; break }
    New-Item -ItemType Directory -Force -Path (Join-Path $dir 'logs') | Out-Null
    Start-Process -FilePath (Join-Path $dir 'node.exe') -ArgumentList 'server.js' -WorkingDirectory $dir -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $dir 'logs\server.log') -RedirectStandardError (Join-Path $dir 'logs\errors.log')
    for ($i = 0; $i -lt 10 -and -not (Listening); $i++) { Start-Sleep -Milliseconds 500 }
    if (Listening) { Ok "Сайт запущен: http://localhost:$port" } else { Bad "Сайт не запустился. Пришлите файл $dir\logs\errors.log" }
  }
  'stop' {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen
    if (-not $c) { Ok "Сайт на порту $port не запущен"; break }
    $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
    Ok "Сайт на порту $port остановлен (proba-lab.ru не затронут)"
  }
  'check' {
    if (Test-Path (Join-Path $dir 'node.exe')) { Ok 'node.exe на месте' } else { Bad "Нет node.exe в $dir — скопируйте из D:\proba" }
    if (Test-Path (Join-Path $dir 'OBSHCHIJ-CADDY.txt')) { Ok 'Режим «общий Caddy»' } else { Bad 'Нет OBSHCHIJ-CADDY.txt' }
    if (schtasks /Query /TN 'med - sajt' 2>$null) { Ok 'Автозапуск «med - sajt» включён' } else { Bad 'Автозапуск не включён: запустите 2-VKLYUCHIT-AVTOZAPUSK.bat' }
    try { $r = Invoke-WebRequest "http://localhost:$port/api/health" -UseBasicParsing -TimeoutSec 5; if ($r.Content -match $domain) { Ok "Сайт открывается на этом компьютере: http://localhost:$port" } else { Bad "На порту $port отвечает не этот сайт" } } catch { Bad "Сайт не отвечает на http://localhost:$port — запустите ZAPUSTIT-SAJT.bat" }
    $ips = @((Resolve-DnsName $domain -Type A -Server 8.8.8.8 -DnsOnly | Where-Object { $_.IPAddress }).IPAddress)
    if ($ips -contains $serverIp) { Ok "$domain указывает на этот сервер" } elseif ($ips.Count) { Bad "$domain указывает на $($ips -join ', '), а нужно $serverIp (шаг 1)" } else { Bad "$domain пока не найден в DNS — подождите до суток (шаг 1)" }
    try { $r = Invoke-WebRequest "https://$domain/api/health" -UseBasicParsing -TimeoutSec 10; if ($r.Content -match $domain) { Ok "HTTPS для $domain работает" } else { Bad "По https://$domain отвечает другой сайт — проверьте блоки в Caddyfile (шаг 6)" } } catch { Bad "HTTPS для $domain не работает: DNS ещё не обновился или блоки не добавлены в Caddyfile (шаги 1 и 6)" }
    if ($cfg.SMTP_USER -and $cfg.SMTP_PASS) { Ok 'Почта для заявок заполнена' } else { Bad 'Почта для заявок не заполнена (nastrojki.txt)' }
    if ($cfg.B24_WEBHOOK) { Ok 'Вебхук Битрикс24 заполнен' } else { Write-Host '[--] Битрикс24 не подключён (необязательно)' }
  }
}
