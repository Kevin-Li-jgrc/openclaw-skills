#Requires -Version 5.1

<#
.SYNOPSIS
    OpenClaw Skill: 读取加密的Excel/Word文档
.DESCRIPTION
    使用Microsoft Office COM接口读取非标准格式的加密文档
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("excel", "word")]
    [string]$Type,
    
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    
    [Parameter(Mandatory = $false)]
    [int]$MaxRows = 0,
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("text", "json")]
    [string]$Format = "text"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Read-EncryptedExcel {
    param($Path, $MaxRows, $OutputFormat)
    
    $excel = $null
    $workbook = $null
    
    try {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        
        $workbook = $excel.Workbooks.Open($Path)
        $sheet = $workbook.Sheets.Item(1)
        $usedRange = $sheet.UsedRange
        $rowCount = $usedRange.Rows.Count
        $colCount = $usedRange.Columns.Count
        
        if ($MaxRows -gt 0) {
            $rowCount = [Math]::Min($rowCount, $MaxRows)
        }
        
        $result = @{
            SheetName = $sheet.Name
            RowCount = $rowCount
            ColCount = $colCount
            Headers = @()
            Data = @()
        }
        
        # 读取表头（假设第2行是表头）
        for ($col = 1; $col -le $colCount; $col++) {
            $header = $sheet.Cells.Item(2, $col).Text
            $result.Headers += $header
        }
        
        # 读取数据（从第3行开始）
        for ($row = 3; $row -le $rowCount; $row++) {
            $rowData = @{}
            for ($col = 1; $col -le $colCount; $col++) {
                $header = $result.Headers[$col - 1]
                $cellValue = $sheet.Cells.Item($row, $col).Text
                $rowData[$header] = $cellValue
            }
            $result.Data += $rowData
        }
        
        if ($OutputFormat -eq "json") {
            $result | ConvertTo-Json -Depth 10
        } else {
            Write-Host "工作表: $($result.SheetName)"
            Write-Host "总行数: $($result.RowCount)"
            Write-Host "总列数: $($result.ColCount)"
            Write-Host ""
            Write-Host "表头: $($result.Headers -join " | ")"
            Write-Host ""
            Write-Host "=== 数据 ==="
            foreach ($row in $result.Data) {
                $rowValues = @()
                foreach ($header in $result.Headers) {
                    $rowValues += $row[$header]
                }
                Write-Host ($rowValues -join " | ")
            }
        }
    }
    catch {
        Write-Error "读取Excel失败: $($_.Exception.Message)"
    }
    finally {
        if ($workbook) { $workbook.Close($false) }
        if ($excel) { 
            $excel.Quit()
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
        }
    }
}

function Read-EncryptedWord {
    param($Path, $OutputFormat)
    
    $word = $null
    $doc = $null
    
    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        # Word COM expects WdAlertLevel enum; 0 = wdAlertsNone
        $word.DisplayAlerts = 0
        
        $doc = $word.Documents.Open($Path)
        
        $result = @{
            FileName = $doc.Name
            ParagraphCount = $doc.Paragraphs.Count
            Content = $doc.Content.Text
        }
        
        if ($OutputFormat -eq "json") {
            $result | ConvertTo-Json
        } else {
            Write-Host "文件名: $($result.FileName)"
            Write-Host "段落数: $($result.ParagraphCount)"
            Write-Host ""
            Write-Host "=== 内容 ==="
            Write-Host $result.Content
        }
    }
    catch {
        Write-Error "读取Word失败: $($_.Exception.Message)"
    }
    finally {
        if ($doc) { $doc.Close($false) }
        if ($word) { 
            $word.Quit()
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
        }
    }
}

# 主逻辑
switch ($Type) {
    "excel" { Read-EncryptedExcel -Path $FilePath -MaxRows $MaxRows -OutputFormat $Format }
    "word" { Read-EncryptedWord -Path $FilePath -OutputFormat $Format }
}
