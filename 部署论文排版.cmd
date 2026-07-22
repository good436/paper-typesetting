@echo off
chcp 65001 >nul
echo ============================================
echo   论文排版工具 - 一键部署到服务器
echo ============================================
echo.

echo [1/3] 推送代码到 GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo ❌ 推送失败！请检查网络或GitHub权限
    pause
    exit /b 1
)
echo ✅ 推送成功

echo.
echo [2/3] 服务器拉取代码并重启服务...
ssh -o StrictHostKeyChecking=no root@8.134.164.52 "bash /opt/paper-typesetting/update.sh"
if %errorlevel% neq 0 (
    echo ❌ 服务器更新失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 验证服务状态...
ssh -o StrictHostKeyChecking=no root@8.134.164.52 "systemctl is-active paper-typesetting && echo ✅ 服务运行中"
echo.
echo ============================================
echo   部署完成！
echo   访问: http://casemaker.help/paper
echo ============================================
pause
