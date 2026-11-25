; Instalador de San Francisco Crust Pizza (NSIS 3)
; Compilar:  makensis instalador.nsi   (requiere la carpeta dist\SanFranciscoCrustPizza)
Unicode true
!include "MUI2.nsh"

!define APPNAME "San Francisco Crust Pizza"
!define EXENAME "SanFranciscoCrustPizza.exe"
!define VERSION "1.0.0"
!ifndef DISTDIR
  !define DISTDIR "dist\SanFranciscoCrustPizza"
!endif

Name "${APPNAME}"
OutFile "SanFranciscoCrustPizza_Instalador_v${VERSION}.exe"
InstallDir "C:\SanFranciscoCrustPizza\app"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APPNAME} · Sistema Inteligente de Decisiones Comerciales"
!define MUI_ICON "recursos\icono.ico"
!define MUI_UNICON "recursos\icono.ico"
!define MUI_WELCOMEPAGE_TITLE "Instalación de ${APPNAME}"
!define MUI_WELCOMEPAGE_TEXT "Este asistente instalará el Sistema Inteligente de Información y Decisiones Comerciales.$\r$\n$\r$\nNo necesita Python ni conexión a internet. Los datos se guardarán en C:\SanFranciscoCrustPizza\data (o en su perfil de usuario si no hay permisos).$\r$\n$\r$\nPulse Siguiente para continuar."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${EXENAME}"
!define MUI_FINISHPAGE_RUN_TEXT "Iniciar ${APPNAME} ahora"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Section "Aplicación" SecApp
  SetOutPath "$INSTDIR"
  File /r "${DISTDIR}\*.*"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Detener ${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "--detener" "$INSTDIR\${EXENAME}" 0
  CreateShortcut "$SMPROGRAMS\${APPNAME}\Desinstalar.lnk" "$INSTDIR\Desinstalar.exe"
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanFranciscoCrustPizza" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanFranciscoCrustPizza" "UninstallString" "$INSTDIR\Desinstalar.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanFranciscoCrustPizza" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanFranciscoCrustPizza" "DisplayIcon" "$INSTDIR\${EXENAME}"
SectionEnd

Section "Uninstall"
  ExecWait '"$INSTDIR\${EXENAME}" --detener --silencioso'
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${EXENAME}"
  Delete "$INSTDIR\Desinstalar.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SanFranciscoCrustPizza"
  MessageBox MB_OK "La aplicación se desinstaló. Sus datos y respaldos se conservan en la carpeta de datos (C:\SanFranciscoCrustPizza\data)."
SectionEnd
