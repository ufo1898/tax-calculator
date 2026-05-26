@echo off
:: ============================================
:: 个税计算器 - 构建脚本
:: 双击即可构建 debug HAP
:: 注意：hvigor 的 PackageHap 有 JBR JIT bug，需要 -Xint 绕过
:: ============================================
set DEVECO_SDK_HOME=C:\Program Files\Huawei\DevEco Studio
set JAVA_HOME=C:\Program Files\Huawei\DevEco Studio\jbr
set PATH=C:\Program Files\Huawei\DevEco Studio\tools\node;%JAVA_HOME%\bin;%PATH%
cd /d "C:\Users\Administrator\DevEcoStudioProjects\tax-calculator"

echo.
echo ========================================
echo   Building tax-calculator HAP...
echo ========================================
echo.
node "C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js" --mode module -p module=entry@default -p product=default -p buildMode=debug assembleHap

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo   Hvigor failed, retrying packaging with -Xint...
    echo ========================================
    java -Xint -Xmx1024m -jar "C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\lib\app_packing_tool.jar" --mode hap --force true --lib-path entry\build\default\intermediates\stripped_native_libs\default --json-path entry\build\default\intermediates\package\default\module.json --resources-path entry\build\default\intermediates\res\default\resources --index-path entry\build\default\intermediates\res\default\resources.index --pack-info-path entry\build\default\outputs\default\pack.info --out-path entry\build\default\outputs\default\entry-default-unsigned.hap --ets-path entry\build\default\intermediates\loader_out\default\ets --pkg-context-path entry\build\default\intermediates\loader\default\pkgContextInfo.json
)

echo.
echo ========================================
echo   Done. HAP: entry\build\default\outputs\default\entry-default-unsigned.hap
echo ========================================
pause
