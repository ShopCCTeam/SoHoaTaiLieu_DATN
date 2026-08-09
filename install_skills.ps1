$ErrorActionPreference = 'Stop'
$src = "E:\SoHoaTaiLieu_DATN\temp_autoskill_repo\SkillBank"
$dst = "E:\SoHoaTaiLieu_DATN\.skills"

# Common foundation skills (Superpowers, Anthropic, Vercel)
$common = @(
    @{ From = "Common\vercel-labs-agent-skills\composition-patterns"; To = "composition-patterns" },
    @{ From = "Common\vercel-labs-agent-skills\react-best-practices"; To = "react-best-practices" },
    @{ From = "Common\vercel-labs-agent-skills\web-design-guidelines"; To = "web-design-guidelines" },
    @{ From = "Common\anthropics-skill\webapp-testing"; To = "webapp-testing" },
    @{ From = "Common\anthropics-skill\frontend-design"; To = "frontend-design" },
    @{ From = "Common\anthropics-skill\doc-coauthoring"; To = "doc-coauthoring" },
    @{ From = "Common\anthropics-skill\pdf"; To = "pdf" },
    @{ From = "Common\superpowers\test-driven-development"; To = "test-driven-development" },
    @{ From = "Common\superpowers\systematic-debugging"; To = "systematic-debugging" },
    @{ From = "Common\superpowers\writing-plans"; To = "writing-plans" },
    @{ From = "Common\superpowers\writing-skills"; To = "writing-skills" },
    @{ From = "Common\superpowers\finishing-a-development-branch"; To = "finishing-a-development-branch" },
    @{ From = "Common\superpowers\using-git-worktrees"; To = "using-git-worktrees" }
)

# Project-specific skills (ConvSkill)
$project = @(
    @{ From = "ConvSkill\english_gpt4_8_GLM4.7\local-pdf-rag-pipeline-with-langchain-and-ollama"; To = "local-pdf-rag-pipeline-with-langchain-and-ollama" },
    @{ From = "ConvSkill\english_gpt4_8\langchain-local-pdf-rag-pipeline"; To = "langchain-local-pdf-rag-pipeline" },
    @{ From = "ConvSkill\english_gpt4_8\fastapi-local-oop-background-task-system"; To = "fastapi-local-oop-background-task-system" },
    @{ From = "ConvSkill\english_gpt4_8_GLM4.7\fastapi-oop-background-task-management-system"; To = "fastapi-oop-background-task-management-system" },
    @{ From = "ConvSkill\english_gpt4_8\fastapi-base64-image-form-submission"; To = "fastapi-base64-image-form-submission" },
    @{ From = "ConvSkill\english_gpt3.5_8_GLM4.7\fastapi-generic-dynamic-filtering-with-pydantic-and-sqlalchemy"; To = "fastapi-generic-dynamic-filtering-with-pydantic-and-sqlalchemy" },
    @{ From = "ConvSkill\english_gpt4_8_GLM4.7\ocr_medical_receipt_extractor"; To = "ocr_medical_receipt_extractor" },
    @{ From = "ConvSkill\english_gpt3.5_8_GLM4.7\ocr-text-to-wikimedia-source-converter"; To = "ocr-text-to-wikimedia-source-converter" },
    @{ From = "ConvSkill\english_gpt4_8\postgresql-inventory-and-price-tracking-schema"; To = "postgresql-inventory-and-price-tracking-schema" },
    @{ From = "ConvSkill\english_gpt3.5_8\postgres-sql-generator-from-english"; To = "postgres-sql-generator-from-english" },
    @{ From = "ConvSkill\english_gpt3.5_8_GLM4.7\postgresgpt-sql-generator"; To = "postgresgpt-sql-generator" },
    @{ From = "ConvSkill\english_gpt4_8_GLM4.7\linux_high_concurrency_sysctl_tuning"; To = "linux_high_concurrency_sysctl_tuning" },
    @{ From = "ConvSkill\english_gpt4_8_GLM4.7\tensorflow-mirroredstrategy-inference-with-transformers"; To = "tensorflow-mirroredstrategy-inference-with-transformers" },
    @{ From = "ConvSkill\english_gpt4_8\tensorflow-multi-gpu-batch-text-generation"; To = "tensorflow-multi-gpu-batch-text-generation" }
)

$installed = @()
$failed = @()

foreach ($pair in $common + $project) {
    $sourcePath = Join-Path $src $pair.From
    $targetPath = Join-Path $dst $pair.To
    if (Test-Path $sourcePath) {
        try {
            Copy-Item -Recurse -Force $sourcePath $targetPath
            $installed += $pair.To
        } catch {
            $failed += "$($pair.To): $_"
        }
    } else {
        $failed += "$($pair.To): source not found at $sourcePath"
    }
}

Write-Host "=== INSTALLED ===" -ForegroundColor Green
$installed | ForEach-Object { Write-Host "  + $_" }
Write-Host ""
Write-Host "=== FAILED ===" -ForegroundColor Red
$failed | ForEach-Object { Write-Host "  - $_" }
Write-Host ""
Write-Host "Total installed: $($installed.Count)"
Write-Host "Total failed: $($failed.Count)"
