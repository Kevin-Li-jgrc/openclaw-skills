#Requires -Version 5.1

<#
.SYNOPSIS
    读取加密的Excel文件（非标准格式）
.DESCRIPTION
    使用Excel COM接口读取加密的Excel文件，支持输出为文本或JSON格式
.PARAMETER FilePath
    Excel文件路径
.PARAMETER MaxRows
    最大输出行数（默认全部输出）
.PARAMETER Format
    输出格式：text 或 json（默认text）
.EXAMPLE
    Read-EncryptedExcel -FilePath "C:\test.xlsx" -MaxRows 50
.EXAMPLE
    Read-EncryptedExcel -FilePath "C:\test.xlsx" -Format json
#>
function Read-EncryptedExcel {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        
        [Parameter(Mandatory = $false)]
        [int]$MaxRows = 0,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet("text", "json")]
        [string]$Format = "text"
    )
    
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    
    $excel = $null
    $workbook = $null
    
    try {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        
        $workbook = $excel.Workbooks.Open($FilePath)
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
        
        $workbook.Close($false)
        
        if ($Format -eq "json") {
            return $result | ConvertTo-Json -Depth 10
        } else {
            $output = "工作表: $($result.SheetName)`n"
            $output += "总行数: $($result.RowCount)`n"
            $output += "总列数: $($result.ColCount)`n"
            $output += "`n表头: $($result.Headers -join " | ")`n"
            $output += "`n=== 数据 ===`n"
            foreach ($row in $result.Data) {
                $rowValues = @()
                foreach ($header in $result.Headers) {
                    $rowValues += $row[$header]
                }
                $output += ($rowValues -join " | ") + "`n"
            }
            return $output
        }
    }
    catch {
        Write-Error "读取Excel失败: $($_.Exception.Message)"
        return $null
    }
    finally {
        if ($workbook) {
            $workbook.Close($false)
        }
        if ($excel) {
            $excel.Quit()
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
        }
    }
}

<#
.SYNOPSIS
    读取加密的Word文件（非标准格式）
.DESCRIPTION
    使用Word COM接口读取加密的Word文件
.PARAMETER FilePath
    Word文件路径
.PARAMETER Format
    输出格式：text 或 json（默认text）
.EXAMPLE
    Read-EncryptedWord -FilePath "C:\test.docx"
.EXAMPLE
    Read-EncryptedWord -FilePath "C:\test.docx" -Format json
#>
function Read-EncryptedWord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet("text", "json")]
        [string]$Format = "text"
    )
    
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    
    $word = $null
    $doc = $null
    
    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        # Word COM expects WdAlertLevel enum; 0 = wdAlertsNone
        $word.DisplayAlerts = 0
        
        $doc = $word.Documents.Open($FilePath)
        
        $result = @{
            FileName = $doc.Name
            ParagraphCount = $doc.Paragraphs.Count
            Content = $doc.Content.Text
        }
        
        $doc.Close($false)
        
        if ($Format -eq "json") {
            return $result | ConvertTo-Json
        } else {
            $output = "文件名: $($result.FileName)`n"
            $output += "段落数: $($result.ParagraphCount)`n"
            $output += "`n=== 内容 ===`n"
            $output += $result.Content
            return $output
        }
    }
    catch {
        Write-Error "读取Word失败: $($_.Exception.Message)"
        return $null
    }
    finally {
        if ($doc) {
            $doc.Close($false)
        }
        if ($word) {
            $word.Quit()
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
        }
    }
}

# 导出函数
Export-ModuleMember -Function Read-EncryptedExcel, Read-EncryptedWord
