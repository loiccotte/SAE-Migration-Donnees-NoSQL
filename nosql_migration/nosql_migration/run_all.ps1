Param(
  [Parameter(Mandatory=$false)][string]$CsvDir = ".\csv",

  [Parameter(Mandatory=$true)][string]$PgHost,
  [Parameter(Mandatory=$false)][int]$PgPort = 5432,
  [Parameter(Mandatory=$true)][string]$PgDb,
  [Parameter(Mandatory=$true)][string]$PgUser,
  [Parameter(Mandatory=$true)][string]$PgPassword,

  [Parameter(Mandatory=$false)][string]$NeoUri = "bolt://127.0.0.1:7687",
  [Parameter(Mandatory=$false)][string]$NeoUser = "neo4j",
  [Parameter(Mandatory=$true)][string]$NeoPassword,

  [switch]$TruncateNeo4j
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$env:PYTHONUTF8 = "1"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Run-Cmd {
  param([string]$CmdLabel, [scriptblock]$Command)
  Write-Host $CmdLabel
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Échec ($CmdLabel) - code $LASTEXITCODE"
  }
}

if (-not (Test-Path $CsvDir)) {
  throw "Dossier CSV introuvable: $CsvDir (attendu: .\csv à la racine du projet)"
}

Run-Cmd "1) Création des tables PostgreSQL (DDL) [pg8000]..." {
  py -3 ".\run_ddl_postgres_pg8000.py" `
    --pg-host "$PgHost" --pg-port "$PgPort" --pg-db "$PgDb" --pg-user "$PgUser" --pg-password "$PgPassword" `
    --ddl-path (Join-Path $ScriptDir "sql_ddl_postgres.sql")
}

Run-Cmd "2) Chargement des CSV dans PostgreSQL [pg8000]..." {
  py -3 ".\load_csvs_to_postgres_pg8000.py" `
    --csv-dir "$CsvDir" --pg-host "$PgHost" --pg-port "$PgPort" --pg-db "$PgDb" --pg-user "$PgUser" --pg-password "$PgPassword"
}

if ($TruncateNeo4j) {
  Run-Cmd "3) Migration PostgreSQL -> Neo4j [pg8000]..." {
    py -3 ".\migrate_pg_to_neo4j_pg8000.py" `
      --pg-host "$PgHost" --pg-port "$PgPort" --pg-db "$PgDb" --pg-user "$PgUser" --pg-password "$PgPassword" `
      --neo-uri "$NeoUri" --neo-user "$NeoUser" --neo-password "$NeoPassword" `
      --truncate-neo4j
  }
} else {
  Run-Cmd "3) Migration PostgreSQL -> Neo4j [pg8000]..." {
    py -3 ".\migrate_pg_to_neo4j_pg8000.py" `
      --pg-host "$PgHost" --pg-port "$PgPort" --pg-db "$PgDb" --pg-user "$PgUser" --pg-password "$PgPassword" `
      --neo-uri "$NeoUri" --neo-user "$NeoUser" --neo-password "$NeoPassword"
  }
}

Write-Host "OK ✅ Terminé."