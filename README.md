# mkmsi
Windows Installer Generator, frontend for the WIX toolset

The script is designed to be run on buld-machines, and automatically include all deliverables. Once bootstrapped, it stores it's configiuration in a json file. It can however also be used to boostrap a WiX project that you later maintain manually.

The script is written in python3.

The following command can bootstrap a WiX install for a 64 bit QT 5.10 Desktop application that is built with msvc 2017 and prepared with windeployqt, as for example, [here](https://github.com/jgaa/whid/blob/master/scripts/package-windows.bat).

I wrote the script to make it easy to create installers for Windows for QT Desktop applications directly in Jenkins pipelines, but it can deploy other projects as well. The main 'feature' is that it makes it easy to add files to the deployment using directory and file pattern matching. That makes it very easy to deploy files from a directory-structure on the disk. The installer use Windows Installer when someone installs the package, and once installed, the package can be removed from "Add or Remove Programs" in Windows.

```cmd
.\mkmsi.py ^
    --auto-create qt ^
    --source-dir "C:\Users\Jarle Aase\src\whid\scripts\dist\windows\whid" ^
    --wix-root "C:\Program Files (x86)\WiX Toolset v3.11" ^
    --license licenses\GPL3.rtf ^
    --merge-module "C:\Program Files (x86)\Common Files\Merge Modules\Microsoft_VC140_CRT_x64.msm" ^
    --add-desktop-shortcut ^
    --project-version 2.0.1 ^
     whid
```
