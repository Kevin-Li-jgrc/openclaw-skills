# 使用示例

## 示例1：读取Excel文件

```powershell
# 读取整个Excel文件
.\scripts\read-encrypted.ps1 -Type excel -FilePath "C:\path\to\file.xlsx"

# 只读取前50行
.\scripts\read-encrypted.ps1 -Type excel -FilePath "C:\path\to\file.xlsx" -MaxRows 50

# 输出为JSON格式
.\scripts\read-encrypted.ps1 -Type excel -FilePath "C:\path\to\file.xlsx" -Format json
```

## 示例2：读取Word文件

```powershell
# 读取Word文件
.\scripts\read-encrypted.ps1 -Type word -FilePath "C:\path\to\file.docx"

# 输出为JSON格式
.\scripts\read-encrypted.ps1 -Type word -FilePath "C:\path\to\file.docx" -Format json
```

## 示例3：在PowerShell脚本中使用

```powershell
# 导入模块（需先切换到skill目录）
Import-Module ".\Read-EncryptedOffice.psm1"

# 读取多个Excel文件
$files = Get-ChildItem "C:\path\to\data\*.xlsx"
foreach ($file in $files) {
    Write-Host "正在读取: $($file.Name)"
    $content = Read-EncryptedExcel -FilePath $file.FullName -MaxRows 10
    Write-Host $content
}

# 读取Word并保存到文本文件
$text = Read-EncryptedWord -FilePath "C:\path\to\report.docx"
$text | Out-File "C:\path\to\output\report.txt" -Encoding UTF8
```

## 示例4：处理读取的数据

```powershell
# 读取Excel并转换为CSV
Import-Module ".\Read-EncryptedOffice.psm1"

$result = Read-EncryptedExcel -FilePath "C:\path\to\data.xlsx" -Format json | ConvertFrom-Json

# 导出为CSV
$csvData = @()
foreach ($row in $result.Data) {
    $obj = New-Object PSObject
    foreach ($header in $result.Headers) {
        $obj | Add-Member -MemberType NoteProperty -Name $header -Value $row.$header
    }
    $csvData += $obj
}

$csvData | Export-Csv -Path "C:\path\to\output\data.csv" -NoTypeInformation -Encoding UTF8
```
