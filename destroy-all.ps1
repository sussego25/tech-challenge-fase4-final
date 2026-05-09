param(
    [string]$Environment = "prod",
    [switch]$Force
)

function Confirm-Action {
    param(
        [string]$Message
    )

    if ($Force) {
        return $true
    }

    Write-Host $Message -ForegroundColor Yellow
    $answer = Read-Host "Digite DESTRUIR para confirmar"
    return $answer -eq 'DESTRUIR'
}

if (-not (Confirm-Action "Este script vai destruir TODA a infraestrutura AWS do projeto Tech-Challenge-fase-4. Isso pode interromper serviços e gerar perda de dados.")) {
    Write-Warning "Confirmação não recebida. Abortando."
    exit 1
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host "Iniciando destruição da infraestrutura..." -ForegroundColor Cyan

if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Error "Terraform não encontrado. Instale terraform e execute novamente."
    exit 1
}

$tfDir = Join-Path $root "tech-challenger\infra\terraform"
Set-Location $tfDir

Write-Host "Inicializando Terraform em $tfDir" -ForegroundColor Cyan
terraform init | Write-Host

Write-Host "Executando terraform destroy para environment=$Environment" -ForegroundColor Cyan
try {
    terraform destroy -auto-approve -var="environment=$Environment"
    Write-Host "✅ Destruição concluída." -ForegroundColor Green
} catch {
    Write-Error "Terraform destroy falhou. Verifique o estado e execute o workflow GitHub .github/workflows/destroy.yml se necessário."
    exit 1
}

Write-Host "Lembre-se: o bucket de estado remoto (se existir) pode precisar ser mantido manualmente para redeploy." -ForegroundColor Yellow
