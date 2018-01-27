# mkmsi
Windows Installer Generator, frontend for the WIX toolset

The script is designed to be run on build-machines, and to automatically include all deliverables. Once bootstrapped, it stores it's configiuration in a json file. It can however also be used to boostrap a WiX project that you later maintain manually.

The script is written in python3.

I wrote the script to make it fast and simple to create installers for Windows for QT Desktop applications directly in Jenkins pipelines. It can deploy other projects as well. The main 'feature' is that it can add files to the deployment using directory and file pattern matching. That makes it very handy to deploy files directly from a directory-structure on the disk. The installer use Windows Installer when someone installs the package, and once installed, the package can be removed from "Add or Remove Programs" in Windows.

## Example
The following command can bootstrap a WiX install for a 64 bit QT 5.10 Desktop application that is built with msvc 2017 and prepared with windeployqt, as for example, [here](https://github.com/jgaa/whid/blob/master/scripts/package-windows.bat).

```cmd
.\mkmsi.py ^
    --auto-create qt ^
    --source-dir "C:\src\whid\scripts\dist\windows\whid" ^
    --wix-root "C:\Program Files (x86)\WiX Toolset v3.11" ^
    --license licenses\GPL3.rtf ^
    --merge-module "C:\Program Files (x86)\Common Files\Merge Modules\Microsoft_VC140_CRT_x64.msm" ^
    --add-desktop-shortcut ^
    --project-version 2.0.1 ^
     whid
```

**All options**
```cmd
src\mkmsi>.\mkmsi.py -h
usage: mkmsi.py [-h] [--auto-create {simple,qt}] [--project-name PROJECT_NAME]
                [--executable EXECUTABLE] [--project-version PROJECT_VERSION]
                [--manufacturer MANUFACTURER] [--version VERSION]
                [--description DESCRIPTION] [--source-dir SOURCE_DIR]
                [--icon ICON] [--add-desktop-shortcut] [--license LICENSE]
                [--full-upgrade] [--wix-root WIX_ROOT]
                [--wix-ui {WixUI_Mondo,WixUI_FeatureTree,WixUI_InstallDir,WixUI_Minimal,WixUI_Advanced}]
                [--wix-banner WIX_BANNER] [--merge-module MERGE_MODULE]
                project

Create a Windows Installer .msi file

positional arguments:
  project               Name of the project, without file extention

optional arguments:
  -h, --help            show this help message and exit
  --auto-create {simple,qt}
                        Create a project-file if required (Required extra
                        arguments should be present)
  --project-name PROJECT_NAME
                        Project name
  --executable EXECUTABLE
                        The main .exe file
  --project-version PROJECT_VERSION
                        Version of the project (n.n.n)
  --manufacturer MANUFACTURER
                        Manufacturer of the project (Person or company name)
  --version VERSION     Version of the project (n.n.n)
  --description DESCRIPTION
                        Description of the application
  --source-dir SOURCE_DIR
                        The root-directory with the files to package
  --icon ICON           Name of the icon file to use
  --add-desktop-shortcut
                        Add a desktop shortcut
  --license LICENSE     The license to use. This must be a text-file in .rtf
                        format.
  --full-upgrade        Make sure the application is reinstalled if it is
                        previously installed
  --wix-root WIX_ROOT   The location where the WiX toolset is installed
  --wix-ui {WixUI_Mondo,WixUI_FeatureTree,WixUI_InstallDir,WixUI_Minimal,WixUI_Advanced}
                        WiX UI flavor to use
  --wix-banner WIX_BANNER
                        Bitmap-file (.bmp) with a banner to show in the
                        installer
  --merge-module MERGE_MODULE
                        Add a merge module (like a VC runtime)
```


## Not an example for best practice...
The code is not pretty, it was written in a rush. I went for ease of use. Everything is in one file, so the script is super-simple to deploy. It has no dependencies, except for Python 3.5 or better. The project files would have looked prettyer in yaml than in javascript. However, pretty was not good enough reason to add a dependency. 

